import { useState } from 'react';
import { ShieldCheck, Lock, User as UserIcon, KeyRound, AlertCircle, ArrowRight, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';
import type { User } from '../types/investigation';

interface LoginScreenProps {
  onLoginSuccess: (user: User) => void;
}

export default function LoginScreen({ onLoginSuccess }: LoginScreenProps) {
  const [isBootstrapMode, setIsBootstrapMode] = useState(false);
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [bootstrapKey, setBootstrapKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim() || !password) {
      setErrorMessage('Please enter both User ID and Password.');
      return;
    }

    try {
      setLoading(true);
      setErrorMessage(null);
      const res = await api.login(userId.trim(), password);
      onLoginSuccess(res.user);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Authentication failed. Please verify your credentials.';
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleBootstrap = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim() || !password) {
      setErrorMessage('Please enter both User ID and Password.');
      return;
    }
    if (password.length < 8) {
      setErrorMessage('Admin password must be at least 8 characters long.');
      return;
    }

    try {
      setLoading(true);
      setErrorMessage(null);
      const res = await api.bootstrapAdmin(userId.trim(), password, displayName.trim(), bootstrapKey.trim());
      onLoginSuccess(res.user);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Bootstrap failed. An administrator may already exist or the key is invalid.';
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden">
      {/* Decorative background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-teal-500/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[300px] bg-indigo-500/10 blur-[100px] rounded-full pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-grid size-14 place-items-center rounded-2xl bg-gradient-to-tr from-slate-900 to-slate-800 border border-slate-700/80 shadow-2xl shadow-teal-500/10 text-teal-400 mb-4">
            <ShieldCheck size={32} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            AI Cyber Investigation Assistant
          </h1>
          <p className="text-xs text-slate-400 mt-1.5 uppercase tracking-widest font-semibold">
            Digital Forensics & Incident Response Platform
          </p>
        </div>

        {/* Authentication Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/90 backdrop-blur-xl p-7 shadow-2xl shadow-black/80">
          <div className="flex items-center justify-between pb-5 mb-5 border-b border-slate-800">
            <div>
              <h2 className="text-base font-semibold text-white">
                {isBootstrapMode ? 'System Bootstrap' : 'Secure Sign In'}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {isBootstrapMode
                  ? 'One-time initial administrator setup'
                  : 'Authorized personnel access only'}
              </p>
            </div>
            <div className="flex items-center gap-1 text-[11px] font-medium text-teal-400 bg-teal-950/60 border border-teal-800/50 px-2.5 py-1 rounded-full">
              <Lock size={12} /> RBAC Protected
            </div>
          </div>

          {errorMessage && (
            <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300">
              <AlertCircle size={16} className="shrink-0 text-rose-400 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {!isBootstrapMode ? (
            /* Standard Login Form */
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  User ID / Badge Identifier
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <UserIcon size={16} />
                  </div>
                  <input
                    type="text"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    placeholder="e.g. inv_kumar or admin"
                    required
                    autoFocus
                    className="w-full pl-9 pr-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <KeyRound size={16} />
                  </div>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    className="w-full pl-9 pr-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700 px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-lg shadow-teal-500/20 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span>Verifying Credentials...</span>
                ) : (
                  <>
                    <span>Authenticate & Access Workspace</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>
          ) : (
            /* One-Time Bootstrap Form */
            <form onSubmit={handleBootstrap} className="space-y-4">
              <div className="p-3 bg-amber-950/30 border border-amber-800/40 rounded-xl text-xs text-amber-300 flex items-start gap-2">
                <ShieldAlert size={16} className="shrink-0 text-amber-400 mt-0.5" />
                <span>
                  This bootstrap procedure is only permitted if zero administrative accounts exist.
                </span>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Initial Admin User ID
                </label>
                <input
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="e.g. admin"
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Display Name / Callsign
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g. Lead System Administrator"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Password (min 8 characters)
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  minLength={8}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Bootstrap Secret Key (Optional / if set on server)
                </label>
                <input
                  type="password"
                  value={bootstrapKey}
                  onChange={(e) => setBootstrapKey(e.target.value)}
                  placeholder="Leave empty if BOOTSTRAP_SECRET_KEY is not configured"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700 px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-lg shadow-teal-500/20 transition disabled:opacity-50"
              >
                {loading ? 'Initializing Administrator...' : 'Bootstrap Primary Administrator'}
              </button>
            </form>
          )}

          {/* Mode Switcher */}
          <div className="mt-6 pt-4 border-t border-slate-800 text-center">
            <button
              type="button"
              onClick={() => {
                setIsBootstrapMode(!isBootstrapMode);
                setErrorMessage(null);
              }}
              className="text-xs text-slate-400 hover:text-teal-400 transition"
            >
              {isBootstrapMode
                ? '← Back to standard personnel login'
                : 'Initial system deployment? Bootstrap administrator account →'}
            </button>
          </div>
        </div>

        {/* Security Notice */}
        <p className="mt-6 text-center text-xs text-slate-500">
          Digital chain-of-custody protected. All forensic sessions are cryptographically signed with Argon2id and JWT verification.
        </p>
      </div>
    </div>
  );
}
