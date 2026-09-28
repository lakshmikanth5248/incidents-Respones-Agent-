"""
Vectorize Hindsight HTTP Client.
Directly encapsulates HTTP communication with the Hindsight service over REST.
Guarantees retries, connection timeouts, and distinct exception mapping.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
import httpx

from src.observability.logger import logger


class HindsightClientError(Exception):
    """Base exception for Hindsight client errors."""
    pass


class HindsightUnavailableError(HindsightClientError):
    """Hindsight memory service is unreachable or returned 5xx."""
    pass


class HindsightTimeoutError(HindsightClientError):
    """Hindsight memory request timed out."""
    pass


class HindsightMalformedResponseError(HindsightClientError):
    """Hindsight returned non-JSON or malformed payload."""
    pass


class HindsightAPIError(HindsightClientError):
    """Hindsight returned an HTTP 4xx or business error."""
    def __init__(self, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class HindsightClient:
    """
    Standard HTTP client for interacting with the Vectorize Hindsight API.
    Conforms to the actual Vectorize REST structure:
      - POST /v1/default/banks/{bank_id}/memories/recall
      - POST /v1/default/banks/{bank_id}/memories/retain
      - GET  /v1/default/banks/{bank_id}/memories/{entry_id}
      - POST /v1/default/banks/{bank_id}/memories/{entry_id}/flag
      - GET  /health
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8888",
        api_key: Optional[str] = None,
        bank_id: str = "incident-response-agent",
        timeout: float = 5.0,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.bank_id = bank_id
        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _execute_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute HTTP request with bounded retry and timeout translation."""
        attempts = 0
        last_exception = None

        while attempts <= self.max_retries:
            attempts += 1
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=self._headers(),
                        **kwargs
                    )

                # Retry on 502, 503, 504
                if response.status_code in (502, 503, 504) and attempts <= self.max_retries:
                    logger.warning(
                        f"hindsight.retryable_status status={response.status_code} attempt={attempts}"
                    )
                    time.sleep(0.1 * (2 ** (attempts - 1)))
                    continue

                if response.status_code >= 500:
                    raise HindsightUnavailableError(
                        f"Hindsight service returned server error {response.status_code}: {response.text}"
                    )

                if response.status_code >= 400:
                    raise HindsightAPIError(
                        f"Hindsight API error {response.status_code}: {response.text}",
                        status_code=response.status_code
                    )

                return response

            except (httpx.ConnectError, httpx.NetworkError) as e:
                last_exception = HindsightUnavailableError(f"Cannot connect to Hindsight service: {str(e)}")
                if attempts <= self.max_retries:
                    time.sleep(0.1 * (2 ** (attempts - 1)))
                    continue
            except httpx.TimeoutException as e:
                last_exception = HindsightTimeoutError(f"Hindsight request timed out after {self.timeout}s: {str(e)}")
                if attempts <= self.max_retries:
                    time.sleep(0.1 * (2 ** (attempts - 1)))
                    continue

        if last_exception:
            raise last_exception
        raise HindsightUnavailableError("Failed to reach Hindsight service after retries.")

    def health_check(self) -> Tuple[bool, str]:
        """Check if Hindsight service is reachable and responsive."""
        url = f"{self.base_url}/health"
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(url, headers=self._headers())
                if res.status_code == 200:
                    return True, "connected"
                return False, f"unhealthy_status_{res.status_code}"
        except Exception as e:
            return False, f"unavailable: {str(e)}"

    def recall(
        self,
        query: str,
        bank_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Call Hindsight recall endpoint."""
        target_bank = bank_id or self.bank_id
        url = f"{self.base_url}/v1/default/banks/{target_bank}/memories/recall"
        payload: Dict[str, Any] = {
            "query": query,
            "budget": "mid",
            "max_tokens": 4096,
        }
        if filters and filters.get("tags"):
            payload["tags"] = filters["tags"]
            payload["tags_match"] = filters.get("tags_match", "any")

        response = self._execute_with_retry("POST", url, json=payload)
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise HindsightMalformedResponseError("Hindsight response is not a JSON object")
            return data
        except ValueError as e:
            raise HindsightMalformedResponseError(f"Failed to parse Hindsight response as JSON: {str(e)}")

    def retain(
        self,
        entry: Dict[str, Any],
        bank_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call Hindsight retain endpoint."""
        target_bank = bank_id or self.bank_id
        url = f"{self.base_url}/v1/default/banks/{target_bank}/memories"

        if "items" in entry:
            payload = entry
        else:
            tags = []
            if entry.get("service"):
                tags.append(f"service:{entry['service']}")
            if entry.get("component"):
                tags.append(f"component:{entry['component']}")
            if entry.get("entry_type"):
                tags.append(f"type:{entry['entry_type']}")
            if entry.get("outcome_label"):
                tags.append(f"outcome:{entry['outcome_label']}")

            body_content = entry.get("body") or entry.get("content") or ""
            context_str = f"Incident {entry.get('source_incident_ref', '')} | Service {entry.get('service', '')}".strip(" |")
            doc_id = str(entry.get("source_incident_ref") or entry.get("document_id") or "incident-doc")

            payload = {
                "items": [
                    {
                        "content": body_content,
                        "context": context_str,
                        "document_id": doc_id,
                        "tags": tags,
                    }
                ],
                "async": False,
            }

        try:
            response = self._execute_with_retry("POST", url, json=payload)
        except HindsightAPIError as err:
            # Fallback for mock servers or legacy endpoints supporting /memories/retain
            if err.status_code in (404, 405):
                fallback_url = f"{self.base_url}/v1/default/banks/{target_bank}/memories/retain"
                response = self._execute_with_retry("POST", fallback_url, json=entry)
            else:
                raise

        try:
            data = response.json()
            if not isinstance(data, dict):
                raise HindsightMalformedResponseError("Hindsight retain response is not a JSON object")
            if "entry_id" not in data:
                data["entry_id"] = entry.get("source_incident_ref") or "retained-entry"
                data["status"] = "stored"
            return data
        except ValueError as e:
            raise HindsightMalformedResponseError(f"Failed to parse Hindsight retain response as JSON: {str(e)}")

    def get_experience(
        self,
        entry_id: str,
        bank_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Call Hindsight get memory endpoint."""
        target_bank = bank_id or self.bank_id
        url = f"{self.base_url}/v1/default/banks/{target_bank}/memories/{entry_id}"

        try:
            response = self._execute_with_retry("GET", url)
            return response.json()
        except HindsightAPIError as e:
            if e.status_code == 404:
                return None
            raise

    def flag_experience(
        self,
        entry_id: str,
        flag_data: Dict[str, Any],
        bank_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call Hindsight flag memory endpoint or curate curation state."""
        target_bank = bank_id or self.bank_id
        patch_url = f"{self.base_url}/v1/default/banks/{target_bank}/memories/{entry_id}"
        patch_payload = {
            "state": "invalidated",
            "reason": flag_data.get("reason", "Flagged by operator"),
        }
        try:
            response = self._execute_with_retry("PATCH", patch_url, json=patch_payload)
            return response.json()
        except HindsightAPIError as e:
            if e.status_code in (404, 405):
                fallback_url = f"{self.base_url}/v1/default/banks/{target_bank}/memories/{entry_id}/flag"
                response = self._execute_with_retry("POST", fallback_url, json=flag_data)
                return response.json()
            raise
