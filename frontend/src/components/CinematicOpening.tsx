import React, { useState, useEffect, useRef } from 'react';

interface CinematicOpeningProps {
  onComplete: () => void;
}

export const CinematicOpening: React.FC<CinematicOpeningProps> = ({ onComplete }) => {
  const [phase, setPhase] = useState<'intro' | 'opening' | 'sweep' | 'complete'>('intro');
  const [skipped, setSkipped] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Check reduced motion
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      onComplete();
      return;
    }

    // Sequence timing
    // 0ms - 800ms: Logo & atmospheric particles focus
    // 800ms: Curtains unlock & start separating smoothly
    // 1800ms: Light sweep passes
    // 2700ms: Complete and hand over to dashboard
    const openTimer = setTimeout(() => {
      setPhase('opening');
    }, 850);

    const sweepTimer = setTimeout(() => {
      setPhase('sweep');
    }, 1750);

    const completeTimer = setTimeout(() => {
      setPhase('complete');
      onComplete();
    }, 2850);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === ' ') {
        skipIntro();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      clearTimeout(openTimer);
      clearTimeout(sweepTimer);
      clearTimeout(completeTimer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onComplete]);

  // Subtle atmospheric particle canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    interface Particle {
      x: number;
      y: number;
      vx: number;
      vy: number;
      size: number;
      alpha: number;
    }

    const particles: Particle[] = Array.from({ length: 45 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: -0.3 - Math.random() * 0.4,
      size: 1 + Math.random() * 1.5,
      alpha: 0.15 + Math.random() * 0.4,
    }));

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.y < 0) p.y = canvas.height;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;

        ctx.fillStyle = `rgba(0, 240, 255, ${p.alpha * 0.6})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  const skipIntro = () => {
    if (skipped) return;
    setSkipped(true);
    setPhase('complete');
    onComplete();
  };

  if (phase === 'complete') return null;

  const isOpening = phase === 'opening' || phase === 'sweep';

  return (
    <div className="fixed inset-0 z-[100] pointer-events-auto overflow-hidden select-none">
      {/* Background Particles Canvas (sits behind curtains) */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none z-10"
      />

      {/* Skip Button */}
      <button
        onClick={skipIntro}
        className="absolute top-5 right-6 z-50 px-3 py-1.5 rounded bg-[#181c21]/80 hover:bg-[#272a30] text-[#b9cacb] hover:text-[#00f0ff] font-mono text-[11px] font-bold border border-[#3b494b]/50 backdrop-blur-md transition-all flex items-center gap-1.5 cursor-pointer shadow-lg"
      >
        <span>SKIP INTRO</span>
        <span className="text-[9px] px-1 py-0.2 rounded bg-[#0b0e13] text-[#7bd0ff] border border-[#3b494b]">
          ESC
        </span>
      </button>

      {/* Left Curtain */}
      <div
        className={`absolute top-0 bottom-0 left-0 w-1/2 z-30 transition-transform duration-[1700ms] ease-[cubic-bezier(0.77,0,0.175,1)] shadow-[15px_0_40px_rgba(0,0,0,0.95)] flex justify-end ${
          isOpening ? '-translate-x-full' : 'translate-x-0'
        }`}
        style={{
          background: 'linear-gradient(135deg, #07090d 0%, #0d1117 60%, #121822 100%)',
        }}
      >
        {/* Aerospace Surface Texture & Seams */}
        <div className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(#3b494b_1px,transparent_1px)] [background-size:24px_24px]" />

        {/* Structural vertical ribbing */}
        <div className="absolute top-0 bottom-0 right-12 w-px bg-[#3b494b]/30" />
        <div className="absolute top-0 bottom-0 right-28 w-px bg-[#3b494b]/20" />

        {/* Tactical Air-Lock Labels */}
        <div className="absolute bottom-8 left-8 font-mono text-[10px] text-[#b9cacb]/40 tracking-widest flex flex-col gap-0.5">
          <span className="text-[#00f0ff]/60">AEGIS COMMAND SPEC // 2026</span>
          <span>AIRLOCK PORT 01-A // SECURED</span>
        </div>

        {/* Vertical Center Seam Bevel */}
        <div className="relative w-1.5 h-full bg-gradient-to-r from-transparent via-[#1a232e] to-[#00f0ff]/30 border-r border-[#00f0ff]/40 shadow-[0_0_12px_rgba(0,240,255,0.3)]" />
      </div>

      {/* Right Curtain */}
      <div
        className={`absolute top-0 bottom-0 right-0 w-1/2 z-30 transition-transform duration-[1700ms] ease-[cubic-bezier(0.77,0,0.175,1)] shadow-[-15px_0_40px_rgba(0,0,0,0.95)] flex justify-start ${
          isOpening ? 'translate-x-full' : 'translate-x-0'
        }`}
        style={{
          background: 'linear-gradient(225deg, #07090d 0%, #0d1117 60%, #121822 100%)',
        }}
      >
        {/* Surface grid */}
        <div className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(#3b494b_1px,transparent_1px)] [background-size:24px_24px]" />

        {/* Structural vertical ribbing */}
        <div className="absolute top-0 bottom-0 left-12 w-px bg-[#3b494b]/30" />
        <div className="absolute top-0 bottom-0 left-28 w-px bg-[#3b494b]/20" />

        {/* Tactical Air-Lock Labels */}
        <div className="absolute bottom-8 right-8 font-mono text-[10px] text-[#b9cacb]/40 tracking-widest text-right flex flex-col gap-0.5">
          <span className="text-[#00f0ff]/60">HINDSIGHT HYPERGRAPH v4.9</span>
          <span>STATUS: INITIALIZING SURVEILLANCE</span>
        </div>

        {/* Vertical Center Seam Bevel */}
        <div className="relative w-1.5 h-full bg-gradient-to-l from-transparent via-[#1a232e] to-[#00f0ff]/30 border-l border-[#00f0ff]/40 shadow-[0_0_12px_rgba(0,240,255,0.3)]" />
      </div>

      {/* Central Emblem & Title Display (Fades & splits during opening) */}
      <div
        className={`absolute inset-0 z-40 flex flex-col items-center justify-center pointer-events-none transition-all duration-700 ${
          isOpening ? 'opacity-0 scale-110 blur-sm' : 'opacity-100 scale-100'
        }`}
      >
        <div className="relative flex flex-col items-center gap-3">
          {/* Cyan Glow Halo */}
          <div className="absolute -inset-10 bg-[#00f0ff]/15 rounded-full blur-2xl animate-pulse" />

          {/* Emblem */}
          <img
            alt="Aegis Command Emblem"
            className="h-16 w-auto object-contain drop-shadow-[0_0_20px_rgba(0,240,255,0.6)] animate-fade-in relative z-10"
            src="https://lh3.googleusercontent.com/aida/AEtjO1W2YjyToyzAKSH7eXM6qMzMWjBT8gn-VWBjFH3qnKZRAgGCi9Nwpq5BKMi0HjAychva1EAm3MOXoT0v0ImBdNCKsfxcS0VHqrYsIgoImc4YPbS2k3dwoy_VgRM4rOJR8TffDRRIi0NsizNhRjpJfYlwbaAkFVFOB97BljNO5bIw777q737u1kb-T1fsmkm1eNXmbsA1h8h6nnrLdGsTUnNs1Ll7d1Uq5S7dWJAxZq5BZMw9WIBgY4GLFqHV"
          />

          <div className="flex flex-col items-center text-center gap-1 relative z-10">
            <h1 className="font-mono text-[24px] md:text-[28px] font-bold text-[#dbfcff] tracking-[0.25em] uppercase">
              AEGIS COMMAND
            </h1>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00f0ff] animate-ping" />
              <span className="font-mono text-[11px] text-[#7bd0ff] tracking-widest uppercase">
                Autonomous Incident Response &amp; Hindsight Engine
              </span>
            </div>
            <span className="font-mono text-[10px] text-[#b9cacb]/70 tracking-wider pt-1">
              ESTABLISHING SRE TELEMETRY LINK...
            </span>
          </div>
        </div>
      </div>

      {/* Subtle Light Sweep Effect across interface upon parting */}
      {isOpening && (
        <div
          className="absolute inset-0 pointer-events-none z-20 transition-opacity duration-1000 animate-sweep"
          style={{
            background:
              'linear-gradient(105deg, transparent 40%, rgba(0, 240, 255, 0.12) 50%, rgba(219, 252, 255, 0.22) 52%, rgba(0, 240, 255, 0.08) 55%, transparent 65%)',
          }}
        />
      )}
    </div>
  );
};
