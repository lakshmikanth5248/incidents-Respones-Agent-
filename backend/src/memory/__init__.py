"""
Memory Module Public Interface.
Only this module communicates with Hindsight (Architectural Invariant).
"""

from src.memory.schemas import (
    MemoryStatus,
    EntryType,
    OutcomeLabel,
    ConfidenceLevel,
    FlagType,
    FlagRecord,
    MemoryEntry,
    MemoryCandidate,
    RecallRequest,
    RecallResult,
    RecallRecord,
    RankingDetail,
    RetainRequest,
    RetainResult,
    RetainEntryResult,
    FlagExperienceRequest,
    FlagExperienceResponse,
)
from src.memory.client import (
    HindsightClient,
    HindsightClientError,
    HindsightUnavailableError,
    HindsightTimeoutError,
    HindsightMalformedResponseError,
    HindsightAPIError,
)
from src.memory.test_double import HindsightTestDouble
from src.memory.service import MemoryService, memory_service
from src.memory.ranking import rank_and_score_entries
from src.memory.query_builder import build_recall_intent, RecallIntent

__all__ = [
    "MemoryStatus",
    "EntryType",
    "OutcomeLabel",
    "ConfidenceLevel",
    "FlagType",
    "FlagRecord",
    "MemoryEntry",
    "MemoryCandidate",
    "RecallRequest",
    "RecallResult",
    "RecallRecord",
    "RankingDetail",
    "RetainRequest",
    "RetainResult",
    "RetainEntryResult",
    "FlagExperienceRequest",
    "FlagExperienceResponse",
    "HindsightClient",
    "HindsightClientError",
    "HindsightUnavailableError",
    "HindsightTimeoutError",
    "HindsightMalformedResponseError",
    "HindsightAPIError",
    "HindsightTestDouble",
    "MemoryService",
    "memory_service",
    "rank_and_score_entries",
    "build_recall_intent",
]
