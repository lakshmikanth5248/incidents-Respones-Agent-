import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { ServiceNode, MemoryPrecedent } from '../types';

interface ThreeTopologySceneProps {
  onSelectNode?: (nodeName: string) => void;
  onSelectPrecedent?: (precedentId: string) => void;
  selectedNodeId?: string | null;
}

export const ThreeTopologyScene: React.FC<ThreeTopologySceneProps> = ({
  onSelectNode,
  onSelectPrecedent,
  selectedNodeId,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredObject, setHoveredObject] = useState<string | null>(null);
  const [isRotating, setIsRotating] = useState<boolean>(true);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Clear previous canvas if any
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    const width = container.clientWidth || 500;
    const height = container.clientHeight || 280;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.set(0, 32, 72);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x0c1e30, 2.5);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x00f0ff, 2.8);
    dirLight.position.set(20, 40, 30);
    scene.add(dirLight);

    const pointLightRed = new THREE.PointLight(0xef4444, 4.5, 65);
    pointLightRed.position.set(0, 4, 0);
    scene.add(pointLightRed);

    // Holographic Grid Ground
    const gridHelper = new THREE.GridHelper(90, 30, 0x00f0ff, 0x112233);
    gridHelper.position.y = -10;
    scene.add(gridHelper);

    // Node Group
    const rootGroup = new THREE.Group();
    scene.add(rootGroup);

    // Materials
    const primaryIncidentMat = new THREE.MeshPhongMaterial({
      color: 0xef4444,
      emissive: 0x7f1d1d,
      shininess: 90,
    });
    const primaryWireMat = new THREE.MeshBasicMaterial({
      color: 0xfca5a5,
      wireframe: true,
    });

    const memoryNodeMat = new THREE.MeshPhongMaterial({
      color: 0x00f0ff,
      emissive: 0x0e7490,
      shininess: 100,
    });

    // Central Incident Node (INC-2048: Payment API)
    const centralGeom = new THREE.OctahedronGeometry(4.5, 1);
    const centralNode = new THREE.Mesh(centralGeom, primaryIncidentMat);
    centralNode.userData = { id: 'INC-2048', name: 'CHECKOUT API (INC-2048)', type: 'incident' };

    const centralWire = new THREE.Mesh(new THREE.OctahedronGeometry(5.2, 1), primaryWireMat);
    centralNode.add(centralWire);
    centralNode.position.set(0, 3, 0);
    rootGroup.add(centralNode);

    // Connected Service Nodes
    const servicePositions = [
      { id: 'payment-gw', name: 'Payment Gateway', pos: [22, 6, -12] as [number, number, number], color: 0xf59e0b, status: 'DEGRADED' },
      { id: 'envoy-mesh', name: 'Auth Svc', pos: [-20, 2, -15] as [number, number, number], color: 0x38bdf8, status: 'STABLE' },
      { id: 'order-core', name: 'Order Core', pos: [18, -2, 16] as [number, number, number], color: 0x38bdf8, status: 'ELEVATED' },
      { id: 'postgres-primary', name: 'Postgres Cluster', pos: [-16, 4, 18] as [number, number, number], color: 0x38bdf8, status: 'STABLE' },
      { id: 'edge-ingress', name: 'Ingress Envoy', pos: [0, 14, -22] as [number, number, number], color: 0x00f0ff, status: 'ROUTING' },
    ];

    const interactiveMeshes: THREE.Mesh[] = [centralNode];
    const serviceMeshes: THREE.Mesh[] = [];

    servicePositions.forEach((svc) => {
      const mesh = new THREE.Mesh(
        new THREE.DodecahedronGeometry(2.5, 0),
        new THREE.MeshPhongMaterial({
          color: svc.color,
          emissive: svc.color === 0xf59e0b ? 0x78350f : 0x075985,
          wireframe: false,
        })
      );
      mesh.position.set(...svc.pos);
      mesh.userData = { id: svc.id, name: svc.name, status: svc.status, type: 'service' };
      rootGroup.add(mesh);
      serviceMeshes.push(mesh);
      interactiveMeshes.push(mesh);

      // Connection line to central incident
      const lineGeom = new THREE.BufferGeometry().setFromPoints([
        centralNode.position,
        mesh.position,
      ]);
      const lineMat = new THREE.LineDashedMaterial({
        color: svc.color === 0xf59e0b ? 0xf59e0b : 0x0284c7,
        dashSize: 1.5,
        gapSize: 0.8,
      });
      const line = new THREE.Line(lineGeom, lineMat);
      line.computeLineDistances();
      rootGroup.add(line);
    });

    // Memory Nodes (Historical Incidents / Hindsight Layer)
    const memoryNodes = [
      { id: 'INC-1987', name: 'INC-1987 (Payment Cascade)', pos: [-32, 16, 6] as [number, number, number] },
      { id: 'INC-1842', name: 'INC-1842 (Redis Pool)', pos: [30, 18, -4] as [number, number, number] },
      { id: 'INC-1520', name: 'INC-1520 (Auth Storm)', pos: [-24, -5, -28] as [number, number, number] },
      { id: 'INC-2011', name: 'INC-2011 (ES Heap)', pos: [28, -6, 26] as [number, number, number] },
    ];

    const memoryMeshes: THREE.Mesh[] = [];
    memoryNodes.forEach((mem) => {
      const mesh = new THREE.Mesh(
        new THREE.IcosahedronGeometry(2, 0),
        memoryNodeMat.clone()
      );
      mesh.position.set(...mem.pos);
      mesh.userData = { id: mem.id, name: mem.name, type: 'memory' };
      rootGroup.add(mesh);
      memoryMeshes.push(mesh);
      interactiveMeshes.push(mesh);
    });

    // Holographic Memory Recall Beam (From INC-1987 to INC-2048)
    const recallCurve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(-32, 16, 6),
      new THREE.Vector3(-14, 22, 2),
      new THREE.Vector3(0, 3, 0)
    );
    const recallPoints = recallCurve.getPoints(50);
    const recallLineGeom = new THREE.BufferGeometry().setFromPoints(recallPoints);
    const recallLineMat = new THREE.LineBasicMaterial({
      color: 0x00f0ff,
      linewidth: 2,
      transparent: true,
      opacity: 0.85,
    });
    const recallLine = new THREE.Line(recallLineGeom, recallLineMat);
    rootGroup.add(recallLine);

    // Atmospheric Dust Particles
    const particleGeom = new THREE.BufferGeometry();
    const particleCount = 200;
    const posArray = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      posArray[i] = (Math.random() - 0.5) * 120;
      posArray[i + 1] = (Math.random() - 0.5) * 60 + 5;
      posArray[i + 2] = (Math.random() - 0.5) * 120;
    }
    particleGeom.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particleMat = new THREE.PointsMaterial({
      size: 0.8,
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.4,
    });
    const particles = new THREE.Points(particleGeom, particleMat);
    scene.add(particles);

    // Mouse Interaction
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onMouseMove = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      // Raycasting for hover tooltip
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes);
      if (intersects.length > 0) {
        const hit = intersects[0].object;
        if (hit.userData?.name) {
          setHoveredObject(`${hit.userData.name} [${hit.userData.type?.toUpperCase()}]`);
        }
      } else {
        setHoveredObject(null);
      }

      if (isDragging) {
        const deltaX = e.clientX - previousMousePosition.x;
        const deltaY = e.clientY - previousMousePosition.y;
        rootGroup.rotation.y += deltaX * 0.006;
        rootGroup.rotation.x += deltaY * 0.004;
        previousMousePosition = { x: e.clientX, y: e.clientY };
      }
    };

    const onClick = () => {
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes);
      if (intersects.length > 0) {
        const hit = intersects[0].object;
        if (hit.userData?.type === 'memory' && onSelectPrecedent) {
          onSelectPrecedent(hit.userData.id);
        } else if (onSelectNode && hit.userData?.id) {
          onSelectNode(hit.userData.id);
        }
      }
    };

    const dom = renderer.domElement;
    dom.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mouseup', onMouseUp);
    dom.addEventListener('mousemove', onMouseMove);
    dom.addEventListener('click', onClick);

    // Touch support for mobile / tablets
    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        isDragging = true;
        previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
    };
    const onTouchEnd = () => { isDragging = false; };
    const onTouchMove = (e: TouchEvent) => {
      if (isDragging && e.touches.length === 1) {
        const deltaX = e.touches[0].clientX - previousMousePosition.x;
        const deltaY = e.touches[0].clientY - previousMousePosition.y;
        rootGroup.rotation.y += deltaX * 0.006;
        rootGroup.rotation.x += deltaY * 0.004;
        previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
    };

    dom.addEventListener('touchstart', onTouchStart, { passive: true });
    window.addEventListener('touchend', onTouchEnd);
    dom.addEventListener('touchmove', onTouchMove, { passive: true });

    // Animation Loop
    const clock = new THREE.Clock();
    let animId: number;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Gentle passive orbit when not dragging
      if (!isDragging && isRotating) {
        rootGroup.rotation.y += 0.0025;
      }

      // Pulse active incident node
      const scale = 1 + 0.08 * Math.sin(elapsedTime * 3.5);
      centralNode.scale.set(scale, scale, scale);
      centralWire.rotation.y += 0.015;
      centralWire.rotation.z += 0.01;

      // Orbiting subtle rotation for memory nodes
      memoryMeshes.forEach((m, idx) => {
        m.rotation.y += 0.01 + idx * 0.002;
        m.rotation.x += 0.008;
      });

      // Pulse recall beam opacity
      recallLineMat.opacity = 0.5 + 0.4 * Math.sin(elapsedTime * 4.0);

      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || 500;
      const h = container.clientHeight || 280;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      dom.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mouseup', onMouseUp);
      dom.removeEventListener('mousemove', onMouseMove);
      dom.removeEventListener('click', onClick);
      dom.removeEventListener('touchstart', onTouchStart);
      window.removeEventListener('touchend', onTouchEnd);
      dom.removeEventListener('touchmove', onTouchMove);
      renderer.dispose();
      if (container.contains(dom)) {
        container.removeChild(dom);
      }
    };
  }, [isRotating, onSelectNode, onSelectPrecedent]);

  return (
    <div className="relative w-full h-full min-h-[260px] flex items-center justify-center overflow-hidden rounded-xl bg-surface-container-lowest border border-outline-variant/30">
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Floating HUD Badges inside 3D Scene */}
      <div className="absolute top-2 left-3 flex items-center gap-2 pointer-events-none">
        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-high/90 backdrop-blur-md text-[10px] font-mono text-primary border border-primary/20">
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping" />
          HOLOGRAPHIC TOPOLOGY 3D
        </span>
        {hoveredObject && (
          <span className="px-2 py-0.5 rounded bg-surface-container-highest/90 text-[11px] font-mono text-tertiary border border-tertiary/30 animate-fade-in">
            {hoveredObject}
          </span>
        )}
      </div>

      {/* Control buttons */}
      <div className="absolute bottom-2 right-3 flex items-center gap-1 z-10">
        <button
          onClick={() => setIsRotating(!isRotating)}
          className={`px-2 py-1 rounded text-[10px] font-mono transition-colors ${
            isRotating ? 'bg-primary-container/20 text-primary border border-primary/40' : 'bg-surface-container-high text-on-surface-variant'
          }`}
          title={isRotating ? 'Pause rotation' : 'Resume auto-orbit'}
        >
          {isRotating ? 'Auto-Orbit: ON' : 'Auto-Orbit: OFF'}
        </button>
        <span className="text-[10px] font-mono text-on-surface-variant/70 bg-surface-container/60 px-1.5 py-0.5 rounded">
          Drag to Orbit
        </span>
      </div>

      <div className="absolute bottom-2 left-3 flex items-center gap-2 font-mono text-[11px] text-on-surface-variant pointer-events-none">
        <span className="w-2 h-2 rounded-full bg-error animate-pulse" />
        <span>Root Bottleneck: payment-gw-proxy-iad</span>
      </div>
    </div>
  );
};
