import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

interface AuthPagesProps {
  view: 'login' | 'register' | 'forgot-password' | 'profile';
  onNavigate: (view: 'login' | 'register' | 'forgot-password' | 'profile' | 'command' | 'admin' | 'investigation' | 'memory') => void;
}

export const AuthPages: React.FC<AuthPagesProps> = ({ view, onNavigate }) => {
  const { user, login, register, logout } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<'RESPONDER' | 'VIEWER' | 'ANALYST'>('RESPONDER');
  const [error, setError] = useState<string | null>(null);
  const [loadingRole, setLoadingRole] = useState<string | null>(null);
  const [showManualForm, setShowManualForm] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);

  // Quick 1-click launch handler
  const handleQuickLaunch = async (
    targetEmail: string,
    targetRole: string,
    destination: 'command' | 'investigation' | 'memory'
  ) => {
    setError(null);
    setLoadingRole(targetRole);
    try {
      await login(targetEmail, 'password123');
      onNavigate(destination);
    } catch (err: any) {
      setError(err.message || `Failed to authenticate as ${targetRole}`);
    } finally {
      setLoadingRole(null);
    }
  };

  const handleManualLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoadingRole('manual');
    try {
      const authenticatedUser = await login(email, password);
      const isAdm =
        authenticatedUser.role === 'ADMIN' ||
        authenticatedUser.roles?.includes('ADMIN') ||
        authenticatedUser.email.toLowerCase() === 'admin@aegis.corp';

      if (isAdm) {
        onNavigate('admin');
      } else {
        onNavigate('command');
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoadingRole(null);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoadingRole('register');
    try {
      await register(name, email, password, role);
      onNavigate('command');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoadingRole(null);
    }
  };

  // PROFILE VIEW (When user is logged in and views their profile)
  if (view === 'profile' && user) {
    const userRoles = user.roles || [user.role];
    return (
      <div className="flex flex-col w-full max-w-4xl mx-auto gap-5 animate-fade-in py-6">
        <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">verified_user</span>
              <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
                OPERATOR IDENTITY VERIFICATION
              </span>
            </div>
            <h1 className="text-[26px] font-bold text-[#dbfcff]">{user.name}</h1>
            <p className="text-[13px] text-[#b9cacb]">Authenticated SRE Command Personnel</p>
          </div>

          <button
            onClick={() => {
              logout();
              onNavigate('login');
            }}
            className="px-4 py-2 rounded-lg bg-[#93000a]/40 hover:bg-[#93000a] text-[#ffdad6] font-mono text-[12px] font-bold border border-[#ffb4ab]/40 transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">logout</span>
            <span>Sign Out Session</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col items-center text-center gap-3">
            <div className="w-20 h-20 rounded-full bg-[#00f0ff]/20 border-2 border-[#00f0ff] flex items-center justify-center overflow-hidden shadow-[0_0_16px_rgba(0,240,255,0.3)]">
              <img src={user.avatar_url} alt={user.name} className="w-full h-full object-cover" />
            </div>
            <div>
              <h3 className="text-[16px] font-bold text-[#e0e2ea]">{user.name}</h3>
              <span className="text-[12px] font-mono text-[#7bd0ff]">{user.email}</span>
            </div>
            <div className="flex flex-wrap gap-1 justify-center">
              {userRoles.map((r) => (
                <span
                  key={r}
                  className="px-2.5 py-0.5 rounded bg-[#272a30] text-[10px] font-mono font-bold text-[#00f0ff] border border-[#00f0ff]/30"
                >
                  {r}
                </span>
              ))}
            </div>
          </div>

          <div className="md:col-span-2 p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 space-y-3 font-mono text-[12px]">
            <h4 className="text-[14px] font-bold text-[#dbfcff] font-sans border-b border-[#3b494b]/40 pb-2">
              Security Attributes & Authority
            </h4>
            <div className="space-y-2">
              <div className="flex justify-between p-2.5 rounded bg-[#1d2025] border border-[#3b494b]/30">
                <span className="text-[#b9cacb]">User Identifier:</span>
                <span className="text-[#e0e2ea] font-bold">{user.id}</span>
              </div>
              <div className="flex justify-between p-2.5 rounded bg-[#1d2025] border border-[#3b494b]/30">
                <span className="text-[#b9cacb]">Account Created:</span>
                <span className="text-[#e0e2ea]">{new Date(user.created_at).toLocaleString()}</span>
              </div>
              <div className="flex justify-between p-2.5 rounded bg-[#1d2025] border border-[#3b494b]/30">
                <span className="text-[#b9cacb]">Active Authority:</span>
                <span className="text-[#00f0ff] font-bold">
                  {userRoles.join(' • ')}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 3-BUTTON DIRECT LAUNCH STARTING VIEW
  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-[#0b0e13] border border-[#00f0ff]/30 rounded-2xl p-6 md:p-8 shadow-[0_0_40px_rgba(0,240,255,0.15)] flex flex-col gap-6 relative overflow-hidden">
        {/* Ambient glow accents */}
        <div className="absolute -top-24 -right-24 w-56 h-56 bg-[#00f0ff]/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-56 h-56 bg-[#7fecde]/10 rounded-full blur-3xl pointer-events-none" />

        {/* Tactical SRE Terminal Header */}
        <div className="flex flex-col items-center text-center gap-1.5 relative z-10">
          <img
            alt="Aegis Command Emblem"
            className="h-12 w-auto object-contain drop-shadow-[0_0_16px_rgba(0,240,255,0.6)] mb-1"
            src="https://lh3.googleusercontent.com/aida/AEtjO1W2YjyToyzAKSH7eXM6qMzMWjBT8gn-VWBjFH3qnKZRAgGCi9Nwpq5BKMi0HjAychva1EAm3MOXoT0v0ImBdNCKsfxcS0VHqrYsIgoImc4YPbS2k3dwoy_VgRM4rOJR8TffDRRIi0NsizNhRjpJfYlwbaAkFVFOB97BljNO5bIw777q737u1kb-T1fsmkm1eNXmbsA1h8h6nnrLdGsTUnNs1Ll7d1Uq5S7dWJAxZq5BZMw9WIBgY4GLFqHV"
          />
          <h1 className="text-[22px] font-bold text-[#dbfcff] tracking-wider uppercase font-mono">
            AEGIS COMMAND
          </h1>
          <span className="text-[13px] font-mono text-[#00f0ff] font-semibold tracking-wide">
            Memory-Aware Incident Response &amp; Hindsight HyperGraph
          </span>
          <p className="text-[12px] font-mono text-[#b9cacb]/90 max-w-lg mt-1">
            Choose an operational portal below for instant, authorized access:
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-[#93000a]/40 border border-[#ffb4ab]/40 text-[#ffdad6] text-[12px] font-mono flex items-center gap-2 relative z-10">
            <span className="material-symbols-outlined text-[16px] text-[#ffb4ab]">error</span>
            <span>{error}</span>
          </div>
        )}

        {/* THE 3 PRIMARY PORTAL BUTTONS */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative z-10">
          {/* 1. LEAD SRE COMMAND RADAR */}
          <button
            type="button"
            disabled={loadingRole !== null}
            onClick={() => handleQuickLaunch('admin@aegis.corp', 'admin', 'command')}
            className="group relative flex flex-col justify-between p-4 rounded-xl bg-[#141922] hover:bg-[#192230] border border-[#00f0ff]/40 hover:border-[#00f0ff] shadow-lg hover:shadow-[0_0_24px_rgba(0,240,255,0.3)] transition-all text-left cursor-pointer disabled:opacity-50"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="w-8 h-8 rounded-lg bg-[#00f0ff]/20 text-[#00f0ff] flex items-center justify-center material-symbols-outlined text-[20px]">
                  radar
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#00f0ff]/20 text-[#00f0ff] border border-[#00f0ff]/40">
                  LEAD SRE
                </span>
              </div>
              <h3 className="text-[15px] font-bold text-[#dbfcff] group-hover:text-[#00f0ff] transition-colors">
                Live Command Radar
              </h3>
              <p className="text-[11px] text-[#b9cacb] leading-relaxed">
                Real-time telemetry surveillance, topology graphs, and SEV-1 fleet orchestration.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#3b494b]/30 flex items-center justify-between text-[11px] font-mono text-[#00f0ff]">
              <span>{loadingRole === 'admin' ? 'CONNECTING...' : 'Enter as D. Mercer'}</span>
              <span className="material-symbols-outlined text-[14px] group-hover:translate-x-1 transition-transform">
                arrow_forward
              </span>
            </div>
          </button>

          {/* 2. INCIDENT RESPONDER WORKSPACE */}
          <button
            type="button"
            disabled={loadingRole !== null}
            onClick={() => handleQuickLaunch('responder@aegis.corp', 'responder', 'investigation')}
            className="group relative flex flex-col justify-between p-4 rounded-xl bg-[#141922] hover:bg-[#192230] border border-[#f59e0b]/40 hover:border-[#f59e0b] shadow-lg hover:shadow-[0_0_24px_rgba(245,158,11,0.3)] transition-all text-left cursor-pointer disabled:opacity-50"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="w-8 h-8 rounded-lg bg-[#f59e0b]/20 text-[#f59e0b] flex items-center justify-center material-symbols-outlined text-[20px]">
                  psychology
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/40">
                  RESPONDER
                </span>
              </div>
              <h3 className="text-[15px] font-bold text-[#dbfcff] group-hover:text-[#f59e0b] transition-colors">
                Investigation Cockpit
              </h3>
              <p className="text-[11px] text-[#b9cacb] leading-relaxed">
                Active INC-2048 triage, 5-stage cognitive hypothesis reasoning, and runbook approval.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#3b494b]/30 flex items-center justify-between text-[11px] font-mono text-[#f59e0b]">
              <span>{loadingRole === 'responder' ? 'CONNECTING...' : 'Enter as Alex Vance'}</span>
              <span className="material-symbols-outlined text-[14px] group-hover:translate-x-1 transition-transform">
                arrow_forward
              </span>
            </div>
          </button>

          {/* 3. HINDSIGHT EXPERIENCE GRAPH */}
          <button
            type="button"
            disabled={loadingRole !== null}
            onClick={() => handleQuickLaunch('viewer@aegis.corp', 'viewer', 'memory')}
            className="group relative flex flex-col justify-between p-4 rounded-xl bg-[#141922] hover:bg-[#192230] border border-[#10b981]/40 hover:border-[#10b981] shadow-lg hover:shadow-[0_0_24px_rgba(16,185,129,0.3)] transition-all text-left cursor-pointer disabled:opacity-50"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="w-8 h-8 rounded-lg bg-[#10b981]/20 text-[#10b981] flex items-center justify-center material-symbols-outlined text-[20px]">
                  hub
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/40">
                  OBSERVER
                </span>
              </div>
              <h3 className="text-[15px] font-bold text-[#dbfcff] group-hover:text-[#10b981] transition-colors">
                Experience Graph
              </h3>
              <p className="text-[11px] text-[#b9cacb] leading-relaxed">
                3D Interactive constellation of 14,896 historical incident precedents and retained runbooks.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#3b494b]/30 flex items-center justify-between text-[11px] font-mono text-[#10b981]">
              <span>{loadingRole === 'viewer' ? 'CONNECTING...' : 'Enter as Sarah Chen'}</span>
              <span className="material-symbols-outlined text-[14px] group-hover:translate-x-1 transition-transform">
                arrow_forward
              </span>
            </div>
          </button>
        </div>

        {/* COLLAPSIBLE MANUAL LOGIN / REGISTER TOGGLE */}
        <div className="border-t border-[#3b494b]/30 pt-4 flex flex-col items-center gap-3 relative z-10">
          <button
            type="button"
            onClick={() => setShowManualForm(!showManualForm)}
            className="text-[11px] font-mono text-[#7bd0ff] hover:text-[#dbfcff] flex items-center gap-1.5 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[14px]">
              {showManualForm ? 'keyboard_arrow_up' : 'settings'}
            </span>
            <span>{showManualForm ? 'Hide custom credentials form' : 'Advanced: Custom credentials / Registration'}</span>
          </button>

          {showManualForm && (
            <div className="w-full max-w-md bg-[#141922] p-4 rounded-xl border border-[#3b494b]/40 animate-fade-in mt-1">
              <form onSubmit={view === 'register' ? handleRegister : handleManualLogin} className="space-y-3 font-mono text-[12px]">
                {view === 'register' && (
                  <div>
                    <label className="text-[#b9cacb] block mb-1">OPERATOR FULL NAME:</label>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. D. Mercer"
                      className="w-full px-3 py-2 rounded-lg bg-[#181c21] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
                    />
                  </div>
                )}

                <div>
                  <label className="text-[#b9cacb] block mb-1">OPERATOR EMAIL:</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@aegis.corp"
                    className="w-full px-3 py-2 rounded-lg bg-[#181c21] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#b9cacb] block mb-1">PASSPHRASE:</label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full px-3 py-2 rounded-lg bg-[#181c21] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loadingRole !== null}
                  className="w-full py-2 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-bold text-[12px] transition-all cursor-pointer mt-1"
                >
                  {loadingRole ? 'AUTHENTICATING...' : view === 'register' ? 'REGISTER NEW OPERATOR' : 'SIGN IN WITH CREDENTIALS'}
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
