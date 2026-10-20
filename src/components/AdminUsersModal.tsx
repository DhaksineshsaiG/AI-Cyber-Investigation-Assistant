import { useState, useEffect } from 'react';
import { Users, UserPlus, KeyRound, Check, X, Shield, ShieldCheck, AlertCircle, RefreshCw, Lock } from 'lucide-react';
import { api } from '../services/api';
import type { User } from '../types/investigation';

interface AdminUsersModalProps {
  currentUser: User;
  onClose: () => void;
}

export default function AdminUsersModal({ currentUser, onClose }: AdminUsersModalProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // New user form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newUserId, setNewUserId] = useState('');
  const [newDisplayName, setNewDisplayName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<'investigator' | 'admin'>('investigator');
  const [submitting, setSubmitting] = useState(false);

  // Password reset inline state: userId -> password
  const [resettingUserId, setResettingUserId] = useState<string | null>(null);
  const [resetPasswordVal, setResetPasswordVal] = useState('');

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setErrorMessage(null);
      const data = await api.listUsers();
      setUsers(data);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to load user accounts.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserId.trim() || !newDisplayName.trim() || !newPassword) {
      setErrorMessage('All fields are required.');
      return;
    }
    if (newPassword.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMessage(null);
      const created = await api.createUser(newUserId.trim(), newPassword, newDisplayName.trim(), newRole);
      setUsers((prev) => [created, ...prev]);
      setShowAddForm(false);
      setNewUserId('');
      setNewDisplayName('');
      setNewPassword('');
      setNewRole('investigator');
      setSuccessMessage(`Account '${created.user_id}' (${created.role}) created successfully.`);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to create user account.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (targetUser: User) => {
    const newStatus = !targetUser.is_active;

    // Check if target is last active admin
    if (!newStatus && targetUser.role === 'admin') {
      const activeAdmins = users.filter((u) => u.role === 'admin' && u.is_active);
      if (activeAdmins.length <= 1) {
        setErrorMessage('Cannot deactivate the last active administrator.');
        return;
      }
    }

    try {
      setErrorMessage(null);
      const updated = await api.updateUser(targetUser.user_id, { is_active: newStatus });
      setUsers((prev) => prev.map((u) => (u.user_id === updated.user_id ? updated : u)));
      setSuccessMessage(`Account '${targetUser.user_id}' ${newStatus ? 'activated' : 'deactivated'}.`);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to update user status.');
    }
  };

  const handleResetPassword = async (userId: string) => {
    if (!resetPasswordVal || resetPasswordVal.length < 8) {
      setErrorMessage('New password must be at least 8 characters long.');
      return;
    }

    try {
      setErrorMessage(null);
      await api.updateUser(userId, { password: resetPasswordVal });
      setResettingUserId(null);
      setResetPasswordVal('');
      setSuccessMessage(`Password for user '${userId}' was reset successfully.`);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to reset password.');
    }
  };

  const adminCount = users.filter((u) => u.role === 'admin' && u.is_active).length;
  const investigatorCount = users.filter((u) => u.role === 'investigator' && u.is_active).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl border border-slate-700 bg-slate-900 text-white shadow-2xl">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-400">
              <Users size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Personnel & Access Management</h3>
                <span className="rounded-md bg-teal-950/80 border border-teal-700/60 px-2 py-0.5 text-[11px] font-semibold text-teal-300">
                  Admin Control Panel
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Manage investigator dossiers, credentials, and access roles
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-teal-500 hover:bg-teal-600 px-3 py-1.5 text-xs font-semibold text-slate-950 transition"
            >
              <UserPlus size={14} />
              {showAddForm ? 'Cancel' : 'Provision User'}
            </button>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Messages */}
          {errorMessage && (
            <div className="flex items-center justify-between rounded-xl border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300">
              <div className="flex items-center gap-2">
                <AlertCircle size={16} className="text-rose-400 shrink-0" />
                <span>{errorMessage}</span>
              </div>
              <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-rose-200">
                <X size={14} />
              </button>
            </div>
          )}

          {successMessage && (
            <div className="flex items-center justify-between rounded-xl border border-emerald-500/40 bg-emerald-950/40 p-3 text-xs text-emerald-300">
              <div className="flex items-center gap-2">
                <Check size={16} className="text-emerald-400 shrink-0" />
                <span>{successMessage}</span>
              </div>
              <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-emerald-200">
                <X size={14} />
              </button>
            </div>
          )}

          {/* Quick Stats Banner */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
              <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Accounts</div>
              <div className="mt-1 text-xl font-bold text-white">{users.length}</div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
              <div className="text-[11px] font-medium text-teal-400 uppercase tracking-wider">Active Investigators</div>
              <div className="mt-1 text-xl font-bold text-teal-300">{investigatorCount}</div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
              <div className="text-[11px] font-medium text-indigo-400 uppercase tracking-wider">Active Admins</div>
              <div className="mt-1 text-xl font-bold text-indigo-300">{adminCount}</div>
            </div>
          </div>

          {/* Provision User Drawer/Form */}
          {showAddForm && (
            <form onSubmit={handleCreateUser} className="rounded-xl border border-teal-500/30 bg-slate-950 p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-teal-400 flex items-center gap-1.5">
                  <UserPlus size={14} /> Provision New Account
                </h4>
                <span className="text-[11px] text-slate-500">Argon2id Encrypted</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-slate-300 mb-1">User ID / Handle</label>
                  <input
                    type="text"
                    value={newUserId}
                    onChange={(e) => setNewUserId(e.target.value)}
                    placeholder="e.g. inv_vance"
                    required
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-300 mb-1">Display Name / Badge</label>
                  <input
                    type="text"
                    value={newDisplayName}
                    onChange={(e) => setNewDisplayName(e.target.value)}
                    placeholder="e.g. Det. S. Vance (DFIR)"
                    required
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-300 mb-1">Initial Password (min 8 chars)</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    minLength={8}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-300 mb-1">Assigned Role</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value as 'investigator' | 'admin')}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-teal-500"
                  >
                    <option value="investigator">Investigator (Owns & views personal cases only)</option>
                    <option value="admin">Administrator (Full case visibility & user management)</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-600 text-xs font-semibold text-slate-950 transition disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          )}

          {/* User Table */}
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 border-b border-slate-800 text-[11px] text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Personnel</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Last Active</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-900/60">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-400">
                      <RefreshCw size={18} className="animate-spin inline mr-2 text-teal-400" />
                      Loading user accounts...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-400">
                      No accounts registered.
                    </td>
                  </tr>
                ) : (
                  users.map((u) => {
                    const isSelf = u.user_id === currentUser.user_id;
                    const isLastAdmin = u.role === 'admin' && adminCount <= 1;

                    return (
                      <tr key={u.user_id} className="hover:bg-slate-800/40 transition">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-white flex items-center gap-1.5">
                            {u.display_name}
                            {isSelf && (
                              <span className="rounded bg-teal-950 border border-teal-800/60 px-1.5 py-0.2 text-[10px] text-teal-300">
                                You
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-400 font-mono">@{u.user_id}</div>
                        </td>

                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                              u.role === 'admin'
                                ? 'bg-indigo-950/80 text-indigo-300 border border-indigo-800/50'
                                : 'bg-teal-950/80 text-teal-300 border border-teal-800/50'
                            }`}
                          >
                            {u.role === 'admin' ? <ShieldCheck size={12} /> : <Shield size={12} />}
                            {u.role}
                          </span>
                        </td>

                        <td className="px-4 py-3">
                          <span
                            className={`inline-block size-2 rounded-full mr-1.5 ${
                              u.is_active ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-rose-500'
                            }`}
                          />
                          <span className={u.is_active ? 'text-slate-300' : 'text-slate-500'}>
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </td>

                        <td className="px-4 py-3 text-slate-400">
                          {u.last_login_at
                            ? new Date(u.last_login_at).toLocaleDateString()
                            : 'Never'}
                        </td>

                        <td className="px-4 py-3 text-right space-x-2">
                          {/* Reset Password Button / Prompt */}
                          {resettingUserId === u.user_id ? (
                            <div className="inline-flex items-center gap-1.5">
                              <input
                                type="password"
                                placeholder="New Password"
                                value={resetPasswordVal}
                                onChange={(e) => setResetPasswordVal(e.target.value)}
                                className="px-2 py-1 bg-slate-950 border border-slate-700 rounded text-[11px] text-white w-28 focus:outline-none focus:border-teal-500"
                              />
                              <button
                                onClick={() => handleResetPassword(u.user_id)}
                                className="px-2 py-1 bg-teal-500 hover:bg-teal-600 text-slate-950 font-semibold rounded text-[11px]"
                              >
                                Save
                              </button>
                              <button
                                onClick={() => {
                                  setResettingUserId(null);
                                  setResetPasswordVal('');
                                }}
                                className="px-1.5 py-1 text-slate-400 hover:text-white text-[11px]"
                              >
                                <X size={12} />
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => {
                                setResettingUserId(u.user_id);
                                setResetPasswordVal('');
                              }}
                              className="rounded px-2 py-1 border border-slate-700 hover:border-slate-500 text-slate-300 hover:text-white text-[11px] transition inline-flex items-center gap-1"
                              title="Reset account password"
                            >
                              <KeyRound size={11} /> Reset
                            </button>
                          )}

                          {/* Toggle Active Status */}
                          <button
                            onClick={() => handleToggleActive(u)}
                            disabled={isLastAdmin && u.is_active}
                            className={`rounded px-2 py-1 text-[11px] font-medium transition ${
                              u.is_active
                                ? 'border border-rose-800/60 text-rose-300 hover:bg-rose-950/60 disabled:opacity-40 disabled:cursor-not-allowed'
                                : 'border border-emerald-800/60 text-emerald-300 hover:bg-emerald-950/60'
                            }`}
                            title={isLastAdmin ? 'Cannot deactivate the last active administrator' : ''}
                          >
                            {u.is_active ? 'Disable' : 'Enable'}
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="border-t border-slate-800 px-6 py-3 flex items-center justify-between text-xs text-slate-500">
          <span>Protected administrative management console</span>
          <button
            onClick={onClose}
            className="rounded-lg bg-slate-800 hover:bg-slate-700 px-4 py-1.5 text-xs text-white font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
