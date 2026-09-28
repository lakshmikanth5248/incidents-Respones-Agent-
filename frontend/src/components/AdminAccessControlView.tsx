import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { UserAccount } from '../types';
import { useAuth } from '../context/AuthContext';

export const AdminAccessControlView: React.FC = () => {
  const { user: currentUser, refreshUser } = useAuth();
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [modules, setModules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal state for Create / Edit
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserAccount | null>(null);

  // Form fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [selectedRoles, setSelectedRoles] = useState<string[]>(['RESPONDER']);
  const [selectedPerms, setSelectedPerms] = useState<Record<string, boolean>>({});
  const [isActive, setIsActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchUsersAndModules = async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersRes, modulesRes] = await Promise.all([
        api.admin.getUsers(),
        api.admin.getModules(),
      ]);
      setUsers(usersRes.users);
      setModules(modulesRes.modules);
    } catch (err: any) {
      setError(err.message || 'Failed to load user access control list');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsersAndModules();
  }, []);

  const showNotification = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3500);
  };

  const openCreateModal = () => {
    setEditingUser(null);
    setName('');
    setEmail('');
    setPassword('');
    setSelectedRoles(['RESPONDER']);
    const defaultPerms: Record<string, boolean> = {};
    modules.forEach((m) => {
      defaultPerms[m.id] = m.id !== 'admin' && m.id !== 'settings';
    });
    setSelectedPerms(defaultPerms);
    setIsActive(true);
    setIsModalOpen(true);
  };

  const openEditModal = (u: UserAccount) => {
    setEditingUser(u);
    setName(u.name);
    setEmail(u.email);
    setPassword('');
    setSelectedRoles(u.roles || [u.role]);
    setSelectedPerms(u.permissions || {});
    setIsActive(u.is_active !== undefined ? u.is_active : true);
    setIsModalOpen(true);
  };

  const handleRoleToggle = (roleKey: string) => {
    if (selectedRoles.includes(roleKey)) {
      if (selectedRoles.length === 1) return; // Keep at least one role
      const updated = selectedRoles.filter((r) => r !== roleKey);
      setSelectedRoles(updated);
      if (roleKey === 'ADMIN') {
        setSelectedPerms((prev) => ({ ...prev, admin: false }));
      }
    } else {
      const updated = [...selectedRoles, roleKey];
      setSelectedRoles(updated);
      if (roleKey === 'ADMIN') {
        // Automatically enable all permissions for admin
        const allOn: Record<string, boolean> = {};
        modules.forEach((m) => (allOn[m.id] = true));
        setSelectedPerms(allOn);
      }
    }
  };

  const handlePermToggle = (modKey: string) => {
    setSelectedPerms((prev) => ({
      ...prev,
      [modKey]: !prev[modKey],
    }));
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (editingUser) {
        // Update user
        await api.admin.updateUser(editingUser.id, {
          name,
          roles: selectedRoles,
          permissions: selectedPerms,
          is_active: isActive,
          password: password ? password : undefined,
        });
        showNotification(`Operator '${name}' successfully updated.`);
      } else {
        // Create user
        await api.admin.createUser({
          name,
          email,
          password: password || 'password123',
          roles: selectedRoles,
          permissions: selectedPerms,
          is_active: isActive,
        });
        showNotification(`New operator '${name}' created.`);
      }
      setIsModalOpen(false);
      await fetchUsersAndModules();
      refreshUser();
    } catch (err: any) {
      setError(err.message || 'Operation failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteUser = async (id: string, userName: string) => {
    if (!window.confirm(`Are you sure you want to permanently revoke operator account '${userName}'?`)) {
      return;
    }
    try {
      await api.admin.deleteUser(id);
      showNotification(`Operator '${userName}' removed.`);
      fetchUsersAndModules();
    } catch (err: any) {
      setError(err.message || 'Failed to remove user');
    }
  };

  const handleToggleActiveQuick = async (u: UserAccount) => {
    try {
      const newStatus = !u.is_active;
      await api.admin.updateUser(u.id, { is_active: newStatus });
      showNotification(`Account status for ${u.name} set to ${newStatus ? 'ACTIVE' : 'DEACTIVATED'}.`);
      fetchUsersAndModules();
    } catch (err: any) {
      setError(err.message || 'Status update failed');
    }
  };

  const AVAILABLE_ROLES = [
    { key: 'ADMIN', label: 'Admin', desc: 'Full authority & access control', color: 'text-[#ff5c8a] border-[#ff5c8a]/40 bg-[#ff5c8a]/10' },
    { key: 'RESPONDER', label: 'Responder', desc: 'Incident triage & runbooks', color: 'text-[#00f0ff] border-[#00f0ff]/40 bg-[#00f0ff]/10' },
    { key: 'ANALYST', label: 'Analyst', desc: 'Memory synthesis & post-mortem', color: 'text-[#7fecde] border-[#7fecde]/40 bg-[#7fecde]/10' },
    { key: 'VIEWER', label: 'Viewer', desc: 'Read-only observer', color: 'text-[#b9cacb] border-[#3b494b]/40 bg-[#1d2025]' },
  ];

  return (
    <div className="flex flex-col w-full gap-5 animate-fade-in">
      {/* Header Banner */}
      <div className="p-5 rounded-xl bg-[#0b0e13] border border-[#3b494b]/40 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">admin_panel_settings</span>
            <span className="font-mono text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold">
              ADMINISTRATIVE COMMAND CENTER
            </span>
          </div>
          <h1 className="text-[26px] font-bold text-[#dbfcff]">
            Access Control &amp; Fleet Permissions
          </h1>
          <p className="text-[13px] text-[#b9cacb]">
            Manage operator accounts, assign multi-role privileges, and enforce modular safety boundaries.
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="px-4 py-2.5 rounded-lg bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-mono text-[12px] font-bold flex items-center gap-2 shadow-[0_0_15px_rgba(0,240,255,0.3)] transition-all cursor-pointer"
        >
          <span className="material-symbols-outlined text-[18px]">person_add</span>
          <span>Add New Operator</span>
        </button>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="p-3 rounded-lg bg-[#7fecde]/15 border border-[#7fecde]/40 text-[#7fecde] text-[12px] font-mono flex items-center gap-2 animate-fade-in">
          <span className="material-symbols-outlined text-[18px]">check_circle</span>
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-lg bg-[#93000a]/40 border border-[#ffb4ab]/40 text-[#ffdad6] text-[12px] font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] text-[#ffb4ab]">error</span>
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-[#ffb4ab] hover:underline text-[11px]">
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Rack */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <span className="text-[#b9cacb] font-mono text-[11px]">REGISTERED ACCOUNTS</span>
          <span className="text-[26px] font-mono font-bold text-[#dbfcff]">{users.length}</span>
          <span className="text-[11px] font-mono text-[#7fecde]">
            {users.filter((u) => u.is_active).length} Active Sessions
          </span>
        </div>

        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <span className="text-[#b9cacb] font-mono text-[11px]">ADMINISTRATORS</span>
          <span className="text-[26px] font-mono font-bold text-[#ff5c8a]">
            {users.filter((u) => u.roles?.includes('ADMIN') || u.role === 'ADMIN').length}
          </span>
          <span className="text-[11px] font-mono text-[#b9cacb]">Root Authority</span>
        </div>

        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <span className="text-[#b9cacb] font-mono text-[11px]">INCIDENT RESPONDERS</span>
          <span className="text-[26px] font-mono font-bold text-[#00f0ff]">
            {users.filter((u) => u.roles?.includes('RESPONDER') || u.role === 'RESPONDER').length}
          </span>
          <span className="text-[11px] font-mono text-[#b9cacb]">Triage &amp; Runbook Authority</span>
        </div>

        <div className="p-4 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-1">
          <span className="text-[#b9cacb] font-mono text-[11px]">MANAGED MODULES</span>
          <span className="text-[26px] font-mono font-bold text-[#7bd0ff]">{modules.length || 9}</span>
          <span className="text-[11px] font-mono text-[#b9cacb]">Granular RBAC Enforced</span>
        </div>
      </div>

      {/* Operators Table */}
      <div className="p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#7fecde] text-[18px]">manage_accounts</span>
            <h2 className="text-[16px] font-bold text-[#e0e2ea]">Operator Directory &amp; Assigned Roles</h2>
          </div>
          <span className="text-[11px] font-mono text-[#b9cacb]">
            Showing {users.length} authenticated profiles
          </span>
        </div>

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center font-mono text-[12px] text-[#00f0ff]">
            <span className="animate-spin material-symbols-outlined text-[24px] mb-2">sync</span>
            <span>Retrieving Operator Registry...</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-[12px] border-collapse">
              <thead>
                <tr className="border-b border-[#3b494b]/40 text-[#b9cacb] text-[11px] uppercase tracking-wider">
                  <th className="py-2.5 px-3">Operator</th>
                  <th className="py-2.5 px-3">Email Coordinate</th>
                  <th className="py-2.5 px-3">Assigned Roles</th>
                  <th className="py-2.5 px-3">Module Permissions</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#3b494b]/20">
                {users.map((u) => {
                  const uRoles = u.roles || [u.role];
                  const isCurrent = currentUser?.id === u.id;
                  const isRootAdmin = u.email.toLowerCase() === 'admin@aegis.corp';
                  const activePermCount = u.permissions
                    ? Object.values(u.permissions).filter(Boolean).length
                    : modules.length;

                  return (
                    <tr key={u.id} className="hover:bg-[#1d2025]/50 transition-colors">
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2.5">
                          <img
                            src={u.avatar_url}
                            alt={u.name}
                            className="w-7 h-7 rounded-full bg-[#00f0ff]/10 border border-[#00f0ff]/40 object-cover shrink-0"
                          />
                          <div className="flex flex-col">
                            <span className="font-bold text-[#e0e2ea] flex items-center gap-1.5">
                              {u.name}
                              {isCurrent && (
                                <span className="text-[9px] px-1 rounded bg-[#00f0ff]/20 text-[#00f0ff] font-bold">
                                  YOU
                                </span>
                              )}
                            </span>
                            <span className="text-[10px] text-[#849495]">{u.id}</span>
                          </div>
                        </div>
                      </td>

                      <td className="py-3 px-3 text-[#7bd0ff]">{u.email}</td>

                      <td className="py-3 px-3">
                        <div className="flex flex-wrap gap-1">
                          {uRoles.map((r) => {
                            const config = AVAILABLE_ROLES.find((ar) => ar.key === r) || AVAILABLE_ROLES[3];
                            return (
                              <span
                                key={r}
                                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${config.color}`}
                              >
                                {r}
                              </span>
                            );
                          })}
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded bg-[#1d2025] text-[#dbfcff] border border-[#3b494b]/40 text-[11px]">
                          {activePermCount} of {modules.length || 9} modules
                        </span>
                      </td>

                      <td className="py-3 px-3">
                        <button
                          onClick={() => !isRootAdmin && handleToggleActiveQuick(u)}
                          disabled={isRootAdmin}
                          title={isRootAdmin ? 'Root Admin cannot be deactivated' : 'Click to toggle status'}
                          className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 transition-colors ${
                            u.is_active
                              ? 'bg-[#7fecde]/10 text-[#7fecde] border border-[#7fecde]/30 hover:bg-[#7fecde]/20'
                              : 'bg-[#93000a]/20 text-[#ffb4ab] border border-[#ffb4ab]/30 hover:bg-[#93000a]/30'
                          } ${isRootAdmin ? 'cursor-not-allowed opacity-80' : 'cursor-pointer'}`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-[#7fecde]' : 'bg-[#ffb4ab]'}`} />
                          <span>{u.is_active ? 'ACTIVE' : 'INACTIVE'}</span>
                        </button>
                      </td>

                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => openEditModal(u)}
                            className="p-1.5 rounded hover:bg-[#272a30] text-[#00f0ff] transition-colors cursor-pointer"
                            title="Edit roles & permissions"
                          >
                            <span className="material-symbols-outlined text-[16px]">edit</span>
                          </button>

                          {!isRootAdmin && !isCurrent && (
                            <button
                              onClick={() => handleDeleteUser(u.id, u.name)}
                              className="p-1.5 rounded hover:bg-[#93000a]/30 text-[#ffb4ab] transition-colors cursor-pointer"
                              title="Revoke operator"
                            >
                              <span className="material-symbols-outlined text-[16px]">delete</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Module Access Matrix Overview */}
      <div className="p-5 rounded-xl bg-[#181c21] border border-[#3b494b]/40 flex flex-col gap-3 font-mono text-[12px]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#00f0ff] text-[18px]">grid_view</span>
            <h2 className="text-[16px] font-bold text-[#e0e2ea] font-sans">
              System Modules &amp; Access Guardrails
            </h2>
          </div>
          <span className="text-[11px] text-[#b9cacb]">Autonomous Fleet Boundaries</span>
        </div>

        <p className="text-[12px] text-[#b9cacb] font-sans">
          Administrators maintain full control over every subsystem. Assigning or revoking a module immediately restricts navigation and API access for that operator.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
          {modules.map((m) => (
            <div
              key={m.id}
              className="p-3 rounded-lg bg-[#1d2025] border border-[#3b494b]/30 flex flex-col gap-1"
            >
              <div className="flex justify-between items-center">
                <span className="font-bold text-[#dbfcff]">{m.name}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#272a30] text-[#00f0ff] border border-[#00f0ff]/30">
                  {m.id}
                </span>
              </div>
              <p className="text-[11px] text-[#b9cacb] font-sans">{m.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Modal: Create or Edit Operator */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-[#0b0e13] border border-[#00f0ff]/40 rounded-2xl p-6 shadow-[0_0_40px_rgba(0,240,255,0.2)] flex flex-col gap-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-[#3b494b]/40">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#00f0ff] text-[20px]">
                  {editingUser ? 'tune' : 'person_add'}
                </span>
                <h3 className="text-[18px] font-bold text-[#dbfcff]">
                  {editingUser ? `Configure Access: ${editingUser.name}` : 'Provision New Operator Account'}
                </h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-[#b9cacb] hover:text-[#ffdad6] transition-colors cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <form onSubmit={handleSaveUser} className="space-y-4 font-mono text-[12px]">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[#b9cacb] block mb-1">OPERATOR NAME:</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Alex Vance"
                    className="w-full px-3 py-2 rounded bg-[#181c21] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#b9cacb] block mb-1">EMAIL COORDINATE:</label>
                  <input
                    type="email"
                    required
                    disabled={Boolean(editingUser)}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="operator@aegis.corp"
                    className={`w-full px-3 py-2 rounded bg-[#181c21] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none ${
                      editingUser ? 'opacity-60 cursor-not-allowed' : ''
                    }`}
                  />
                </div>
              </div>

              <div>
                <label className="text-[#b9cacb] block mb-1">
                  {editingUser ? 'UPDATE PASSWORD (LEAVE BLANK TO RETAIN CURRENT):' : 'TEMPORARY PASSWORD:'}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={editingUser ? '••••••••••••' : 'Default: password123'}
                  className="w-full px-3 py-2 rounded bg-[#181c21] border border-[#3b494b] text-[#e0e2ea] focus:border-[#00f0ff] focus:outline-none"
                />
              </div>

              {/* Roles Selection */}
              <div>
                <label className="text-[#b9cacb] block mb-1.5 font-bold">
                  ASSIGN ROLES (MULTIPLE ROLES ALLOWED):
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {AVAILABLE_ROLES.map((r) => {
                    const isChecked = selectedRoles.includes(r.key);
                    return (
                      <div
                        key={r.key}
                        onClick={() => handleRoleToggle(r.key)}
                        className={`p-2.5 rounded-lg border cursor-pointer flex items-center justify-between transition-all ${
                          isChecked
                            ? 'bg-[#00f0ff]/15 border-[#00f0ff] text-[#dbfcff] shadow-[0_0_8px_rgba(0,240,255,0.15)]'
                            : 'bg-[#181c21] border-[#3b494b]/40 text-[#b9cacb] hover:bg-[#1d2025]'
                        }`}
                      >
                        <div className="flex flex-col">
                          <span className="font-bold">{r.label}</span>
                          <span className="text-[10px] text-[#849495]">{r.desc}</span>
                        </div>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          className="w-4 h-4 accent-[#00f0ff]"
                        />
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Modular Permissions */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-[#b9cacb] font-bold">MODULE-LEVEL ACCESS CONTROL:</label>
                  <button
                    type="button"
                    onClick={() => {
                      const all: Record<string, boolean> = {};
                      modules.forEach((m) => (all[m.id] = true));
                      setSelectedPerms(all);
                    }}
                    className="text-[#00f0ff] hover:underline text-[10px]"
                  >
                    Select All Modules
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {modules.map((m) => {
                    const hasPerm = Boolean(selectedPerms[m.id]);
                    return (
                      <label
                        key={m.id}
                        className={`p-2 rounded border flex items-center justify-between cursor-pointer transition-colors ${
                          hasPerm
                            ? 'bg-[#1d2025] border-[#7fecde]/50 text-[#e0e2ea]'
                            : 'bg-[#12161b] border-[#3b494b]/30 text-[#849495]'
                        }`}
                      >
                        <span className="truncate text-[11px]">{m.name}</span>
                        <input
                          type="checkbox"
                          checked={hasPerm}
                          onChange={() => handlePermToggle(m.id)}
                          className="w-3.5 h-3.5 accent-[#7fecde] ml-1.5"
                        />
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Status Toggle */}
              <div className="pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-[#e0e2ea]">
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="w-4 h-4 accent-[#00f0ff]"
                  />
                  <span>Account Status: Active &amp; Authorized to Sign In</span>
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#3b494b]/40">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded bg-[#181c21] hover:bg-[#272a30] text-[#b9cacb] transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded bg-[#00f0ff] hover:bg-[#7df4ff] text-[#00363a] font-bold shadow-[0_0_12px_rgba(0,240,255,0.3)] transition-all cursor-pointer"
                >
                  {submitting ? 'Applying Changes...' : editingUser ? 'Save Operator Changes' : 'Create Operator'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
