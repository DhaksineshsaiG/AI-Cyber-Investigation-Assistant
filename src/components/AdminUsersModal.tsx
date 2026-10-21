import { useState, useEffect } from 'react';
import { Users, UserPlus, KeyRound, Check, X, Shield, ShieldCheck, AlertCircle, RefreshCw, Lock, Eye, EyeOff } from 'lucide-react';
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
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [newRole, setNewRole] = useState<'investigator' | 'admin'>('investigator');
  const [submitting, setSubmitting] = useState(false);

  // Password reset inline state
  const [resettingUserId, setResettingUserId] = useState<string | null>(null);
  const [resetPasswordVal, setResetPasswordVal] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);

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
      setSuccessMessage(`Account '${created.user_id}' (${created.role === 'admin' ? 'Administrator' : 'Investigator'}) created successfully.`);
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
      setSuccessMessage(`Account '${targetUser.user_id}' has been ${newStatus ? 'activated' : 'deactivated'}.`);
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
      setShowResetPassword(false);
      setSuccessMessage(`Password for account '${userId}' was reset successfully.`);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to reset password.');
    }
  };

  const adminCount = users.filter((u) => u.role === 'admin' && u.is_active).length;
  const investigatorCount = users.filter((u) => u.role === 'investigator' && u.is_active).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl border border-[#E5E7EB] bg-white text-[#1F2937] shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[#E5E7EB] bg-white px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-[#FFF1F2] border border-[#FECDD3] text-[#C8102E]">
              <Users size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-[#1F2937]">User & Access Management</h3>
                <span className="rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-2 py-0.5 text-[11px] font-bold text-[#C8102E]">
                  Administrator Console
                </span>
              </div>
              <p className="text-xs text-[#6B7280]">
                Create investigator accounts, manage passwords, and configure access permissions
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="inline-flex items-center gap-1.5 rounded-lg btn-royal px-3.5 py-1.5 text-xs font-semibold shadow-xs transition"
            >
              <UserPlus size={14} />
              {showAddForm ? 'Cancel' : 'Create User Account'}
            </button>
            <button
              onClick={onClose}
              aria-label="Close dialog"
              className="rounded-lg p-1.5 text-[#6B7280] hover:bg-slate-100 hover:text-[#1F2937] transition"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-[#F8FAFC]">
          {/* Notifications */}
          {errorMessage && (
            <div className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50 p-3.5 text-xs text-red-800 animate-fadeIn">
              <div className="flex items-center gap-2">
                <AlertCircle size={16} className="text-[#C8102E] shrink-0" />
                <span>{errorMessage}</span>
              </div>
              <button onClick={() => setErrorMessage(null)} className="text-red-600 hover:text-red-900">
                <X size={14} />
              </button>
            </div>
          )}

          {successMessage && (
            <div className="flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 text-xs text-emerald-800 animate-fadeIn">
              <div className="flex items-center gap-2">
                <Check size={16} className="text-emerald-600 shrink-0" />
                <span>{successMessage}</span>
              </div>
              <button onClick={() => setSuccessMessage(null)} className="text-emerald-600 hover:text-emerald-900">
                <X size={14} />
              </button>
            </div>
          )}

          {/* Quick Stats Banner */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
              <div className="text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider">Total Accounts</div>
              <div className="mt-1 text-2xl font-bold text-[#1F2937]">{users.length}</div>
            </div>
            <div className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
              <div className="text-[11px] font-semibold text-[#C8102E] uppercase tracking-wider">Active Investigators</div>
              <div className="mt-1 text-2xl font-bold text-[#C8102E]">{investigatorCount}</div>
            </div>
            <div className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
              <div className="text-[11px] font-semibold text-[#1F2937] uppercase tracking-wider">Active Administrators</div>
              <div className="mt-1 text-2xl font-bold text-[#1F2937]">{adminCount}</div>
            </div>
          </div>

          {/* Create User Form Drawer */}
          {showAddForm && (
            <form onSubmit={handleCreateUser} className="rounded-xl border border-[#FECDD3] bg-white p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#C8102E] flex items-center gap-1.5">
                  <UserPlus size={15} /> Create User Account
                </h4>
                <span className="text-[11px] text-[#6B7280]">Account passwords stored securely</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold text-[#1F2937] mb-1">User ID / Username *</label>
                  <input
                    type="text"
                    value={newUserId}
                    onChange={(e) => setNewUserId(e.target.value)}
                    placeholder="e.g. inv_vance"
                    required
                    className="w-full px-3 py-2 bg-white border border-[#E5E7EB] rounded-lg text-xs text-[#1F2937] placeholder-slate-400 focus:outline-none focus:border-[#C8102E] focus:ring-1 focus:ring-[#C8102E]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#1F2937] mb-1">Full Name / Display Name *</label>
                  <input
                    type="text"
                    value={newDisplayName}
                    onChange={(e) => setNewDisplayName(e.target.value)}
                    placeholder="e.g. Investigator Sarah Vance"
                    required
                    className="w-full px-3 py-2 bg-white border border-[#E5E7EB] rounded-lg text-xs text-[#1F2937] placeholder-slate-400 focus:outline-none focus:border-[#C8102E] focus:ring-1 focus:ring-[#C8102E]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#1F2937] mb-1">Initial Password (min 8 chars) *</label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••••••"
                      required
                      minLength={8}
                      className="w-full pl-3 pr-9 py-2 bg-white border border-[#E5E7EB] rounded-lg text-xs text-[#1F2937] placeholder-slate-400 focus:outline-none focus:border-[#C8102E] focus:ring-1 focus:ring-[#C8102E]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                      className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-[#6B7280] hover:text-[#1F2937]"
                    >
                      {showNewPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#1F2937] mb-1">Access Role *</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value as 'investigator' | 'admin')}
                    className="w-full px-3 py-2 bg-white border border-[#E5E7EB] rounded-lg text-xs text-[#1F2937] focus:outline-none focus:border-[#C8102E] focus:ring-1 focus:ring-[#C8102E]"
                  >
                    <option value="investigator">Investigator (Owns & accesses assigned investigations)</option>
                    <option value="admin">Administrator (Full case visibility & account management)</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-[#E5E7EB]">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-3 py-1.5 rounded-lg border border-[#E5E7EB] text-xs font-semibold text-[#6B7280] hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg btn-royal text-xs font-semibold shadow-xs transition disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          )}

          {/* User Table */}
          <div className="overflow-x-auto rounded-xl border border-[#E5E7EB] bg-white shadow-xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F8FAFC] border-b border-[#E5E7EB] text-[11px] text-[#6B7280] uppercase tracking-wider font-semibold">
                <tr>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Access Role</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Last Active</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E7EB] bg-white">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-[#6B7280]">
                      <RefreshCw size={18} className="animate-spin inline mr-2 text-[#C8102E]" />
                      Loading user accounts...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-[#6B7280]">
                      No accounts registered.
                    </td>
                  </tr>
                ) : (
                  users.map((u) => {
                    const isSelf = u.user_id === currentUser.user_id;
                    const isLastAdmin = u.role === 'admin' && adminCount <= 1;

                    return (
                      <tr key={u.user_id} className="hover:bg-slate-50/80 transition">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-[#1F2937] flex items-center gap-1.5">
                            {u.display_name}
                            {isSelf && (
                              <span className="rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-1.5 py-0.2 text-[10px] font-bold text-[#C8102E]">
                                You
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-[#6B7280] font-mono">@{u.user_id}</div>
                        </td>

                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                              u.role === 'admin'
                                ? 'bg-[#FFF1F2] text-[#C8102E] border border-[#FECDD3]'
                                : 'bg-slate-100 text-[#1F2937] border border-[#E5E7EB]'
                            }`}
                          >
                            {u.role === 'admin' ? <ShieldCheck size={12} /> : <Shield size={12} />}
                            {u.role === 'admin' ? 'Administrator' : 'Investigator'}
                          </span>
                        </td>

                        <td className="px-4 py-3">
                          <span
                            className={`inline-block size-2 rounded-full mr-1.5 ${
                              u.is_active ? 'bg-emerald-500' : 'bg-red-400'
                            }`}
                          />
                          <span className={u.is_active ? 'text-[#1F2937] font-medium' : 'text-[#6B7280]'}>
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </td>

                        <td className="px-4 py-3 text-[#6B7280]">
                          {u.last_login_at
                            ? new Date(u.last_login_at).toLocaleDateString()
                            : 'Never'}
                        </td>

                        <td className="px-4 py-3 text-right space-x-2">
                          {/* Reset Password Inline */}
                          {resettingUserId === u.user_id ? (
                            <div className="inline-flex items-center gap-1.5">
                              <div className="relative">
                                <input
                                  type={showResetPassword ? 'text' : 'password'}
                                  placeholder="New Password"
                                  value={resetPasswordVal}
                                  onChange={(e) => setResetPasswordVal(e.target.value)}
                                  className="pl-2 pr-7 py-1 bg-white border border-[#E5E7EB] rounded text-[11px] text-[#1F2937] w-32 focus:outline-none focus:border-[#C8102E]"
                                />
                                <button
                                  type="button"
                                  onClick={() => setShowResetPassword(!showResetPassword)}
                                  aria-label={showResetPassword ? 'Hide password' : 'Show password'}
                                  className="absolute inset-y-0 right-0 pr-1.5 flex items-center text-[#6B7280]"
                                >
                                  {showResetPassword ? <EyeOff size={12} /> : <Eye size={12} />}
                                </button>
                              </div>
                              <button
                                onClick={() => handleResetPassword(u.user_id)}
                                className="px-2 py-1 btn-royal font-semibold rounded text-[11px]"
                              >
                                Save
                              </button>
                              <button
                                onClick={() => {
                                  setResettingUserId(null);
                                  setResetPasswordVal('');
                                  setShowResetPassword(false);
                                }}
                                aria-label="Cancel password reset"
                                className="px-1.5 py-1 text-[#6B7280] hover:text-[#1F2937] text-[11px]"
                              >
                                <X size={12} />
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => {
                                setResettingUserId(u.user_id);
                                setResetPasswordVal('');
                                setShowResetPassword(false);
                              }}
                              className="rounded px-2.5 py-1 border border-[#E5E7EB] hover:border-[#C8102E] text-[#1F2937] hover:text-[#C8102E] text-[11px] font-medium transition inline-flex items-center gap-1"
                              title="Reset user password"
                            >
                              <KeyRound size={11} /> Reset Password
                            </button>
                          )}

                          {/* Toggle Active Status */}
                          <button
                            onClick={() => handleToggleActive(u)}
                            disabled={isLastAdmin && u.is_active}
                            className={`rounded px-2.5 py-1 text-[11px] font-semibold transition ${
                              u.is_active
                                ? 'border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed'
                                : 'border border-emerald-200 text-emerald-700 hover:bg-emerald-50'
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
        <div className="border-t border-[#E5E7EB] bg-white px-6 py-3.5 flex items-center justify-between text-xs text-[#6B7280]">
          <span>Access control changes are applied immediately</span>
          <button
            onClick={onClose}
            className="rounded-lg border border-[#E5E7EB] hover:bg-slate-100 px-4 py-1.5 text-xs text-[#1F2937] font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
