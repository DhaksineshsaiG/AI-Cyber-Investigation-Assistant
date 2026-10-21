import { useState } from 'react';
import { ShieldCheck, Lock, User as UserIcon, KeyRound, AlertCircle, ArrowRight, ShieldAlert, Eye, EyeOff } from 'lucide-react';
import { api } from '../services/api';
import type { User } from '../types/investigation';

interface LoginScreenProps {
  onLoginSuccess: (user: User) => void;
}

export default function LoginScreen({ onLoginSuccess }: LoginScreenProps) {
  const [isBootstrapMode, setIsBootstrapMode] = useState(false);
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [bootstrapKey, setBootstrapKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedId = userId.trim();
    if (!trimmedId || !password) {
      setErrorMessage('Please enter both your User ID and Password.');
      return;
    }

    try {
      setLoading(true);
      setErrorMessage(null);
      const res = await api.login(trimmedId, password);
      onLoginSuccess(res.user);
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      if (status === 401) {
        setErrorMessage('Incorrect User ID or Password. Please check your credentials and try again.');
      } else if (status === 403) {
        setErrorMessage(detail || 'This account has been disabled or locked. Please reach out to your administrator.');
      } else if (err.code === 'ERR_NETWORK' || !err.response) {
        setErrorMessage(`Unable to reach the investigation backend at ${api.getBaseUrl()}. Please ensure the backend server is running (e.g. 'uvicorn app.main:app --port 8000' in backend) or configure VITE_API_URL in .env.`);
      } else {
        setErrorMessage(detail || 'Authentication failed. Please verify your credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBootstrap = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedId = userId.trim();
    if (!trimmedId || !password) {
      setErrorMessage('Please enter both User ID and Password.');
      return;
    }
    if (password.length < 8) {
      setErrorMessage('Administrator password must be at least 8 characters long.');
      return;
    }

    try {
      setLoading(true);
      setErrorMessage(null);
      const res = await api.bootstrapAdmin(trimmedId, password, displayName.trim(), bootstrapKey.trim());
      onLoginSuccess(res.user);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (err.code === 'ERR_NETWORK' || !err.response) {
        setErrorMessage(`Unable to reach the investigation backend at ${api.getBaseUrl()}. Please ensure the backend server is running or configure VITE_API_URL in .env.`);
      } else {
        setErrorMessage(detail || 'Initial setup failed. An administrator may already exist or the security key was invalid.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-center items-center px-4 py-12 relative">
      {/* Subtle background aesthetics with royal red tint */}
      <div className="absolute top-0 inset-x-0 h-80 bg-gradient-to-b from-[#FFF1F2] to-transparent pointer-events-none" />
      <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-red-100/40 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center size-16 rounded-2xl bg-white border border-[#FECDD3] shadow-md shadow-red-500/10 text-[#C8102E] mb-4">
            <div className="size-12 rounded-xl bg-gradient-to-br from-[#C8102E] to-[#A50F26] flex items-center justify-center text-white shadow-inner">
              <ShieldCheck size={28} />
            </div>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#1F2937]">
            AI Cyber Investigation Assistant
          </h1>
          <p className="text-xs font-semibold text-[#6B7280] mt-1.5 uppercase tracking-wider">
            Secure Digital Evidence & Investigation Workspace
          </p>
        </div>

        {/* Authentication Card */}
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 shadow-xl shadow-slate-200/50">
          <div className="flex items-center justify-between pb-5 mb-6 border-b border-[#E5E7EB]">
            <div>
              <h2 className="text-base font-bold text-[#1F2937]">
                {isBootstrapMode ? 'Initial System Setup' : 'Secure Sign In'}
              </h2>
              <p className="text-xs text-[#6B7280] mt-0.5">
                {isBootstrapMode
                  ? 'Create primary administrator account'
                  : 'Authorized personnel access only'}
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#C8102E] bg-[#FFF1F2] border border-[#FECDD3] px-2.5 py-1 rounded-full">
              <Lock size={12} />
              <span>Access Protected</span>
            </div>
          </div>

          {errorMessage && (
            <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3.5 text-xs text-red-800 animate-fadeIn">
              <AlertCircle size={16} className="shrink-0 text-[#C8102E] mt-0.5" />
              <span className="leading-relaxed">{errorMessage}</span>
            </div>
          )}

          {!isBootstrapMode ? (
            /* Standard Login Form */
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#1F2937] mb-1.5">
                  User ID / Investigator Identifier
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#6B7280]">
                    <UserIcon size={16} />
                  </div>
                  <input
                    type="text"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    placeholder="e.g. inv_kumar or admin"
                    required
                    autoFocus
                    className="w-full pl-9 pr-3 py-2.5 bg-white border border-[#E5E7EB] rounded-xl text-sm text-[#1F2937] placeholder-slate-400 focus:outline-none focus:border-[#C8102E] focus:ring-2 focus:ring-[#C8102E]/15 transition"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-[#1F2937]">
                    Password
                  </label>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#6B7280]">
                    <KeyRound size={16} />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    className="w-full pl-9 pr-10 py-2.5 bg-white border border-[#E5E7EB] rounded-xl text-sm text-[#1F2937] placeholder-slate-400 focus:outline-none focus:border-[#C8102E] focus:ring-2 focus:ring-[#C8102E]/15 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#6B7280] hover:text-[#1F2937] transition"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 inline-flex items-center justify-center gap-2 rounded-xl btn-royal px-4 py-2.5 text-sm font-semibold shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span>Checking credentials...</span>
                ) : (
                  <>
                    <span>Sign In to Workspace</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>
          ) : (
            /* One-Time Bootstrap Form */
            <form onSubmit={handleBootstrap} className="space-y-4">
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2">
                <ShieldAlert size={16} className="shrink-0 text-amber-600 mt-0.5" />
                <span>
                  This initial setup is only available when no administrator account exists in the database.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1F2937] mb-1.5">
                  Initial Administrator User ID
                </label>
                <input
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="e.g. admin"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#E5E7EB] rounded-xl text-sm text-[#1F2937] focus:outline-none focus:border-[#C8102E] focus:ring-2 focus:ring-[#C8102E]/15"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1F2937] mb-1.5">
                  Display Name
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g. Lead System Administrator"
                  className="w-full px-3 py-2 bg-white border border-[#E5E7EB] rounded-xl text-sm text-[#1F2937] focus:outline-none focus:border-[#C8102E] focus:ring-2 focus:ring-[#C8102E]/15"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1F2937] mb-1.5">
                  Password (minimum 8 characters)
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    minLength={8}
                    className="w-full pl-3 pr-10 py-2 bg-white border border-[#E5E7EB] rounded-xl text-sm text-[#1F2937] focus:outline-none focus:border-[#C8102E] focus:ring-2 focus:ring-[#C8102E]/15"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#6B7280] hover:text-[#1F2937]"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1F2937] mb-1.5">
                  Setup Security Key (Optional)
                </label>
                <input
                  type="password"
                  value={bootstrapKey}
                  onChange={(e) => setBootstrapKey(e.target.value)}
                  placeholder="Leave blank if not configured on server"
                  className="w-full px-3 py-2 bg-white border border-[#E5E7EB] rounded-xl text-sm text-[#1F2937] focus:outline-none focus:border-[#C8102E] focus:ring-2 focus:ring-[#C8102E]/15"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 inline-flex items-center justify-center gap-2 rounded-xl btn-royal px-4 py-2.5 text-sm font-semibold shadow-md transition disabled:opacity-50"
              >
                {loading ? 'Creating Administrator...' : 'Create Primary Administrator'}
              </button>
            </form>
          )}

          {/* Mode Switcher */}
          <div className="mt-6 pt-4 border-t border-[#E5E7EB] text-center">
            <button
              type="button"
              onClick={() => {
                setIsBootstrapMode(!isBootstrapMode);
                setErrorMessage(null);
              }}
              className="text-xs font-medium text-[#6B7280] hover:text-[#C8102E] transition"
            >
              {isBootstrapMode
                ? '← Return to standard sign in'
                : 'First-time setup? Initialize primary administrator →'}
            </button>
          </div>
        </div>

        {/* Security Notice */}
        <div className="mt-6 text-center text-xs text-[#6B7280]">
          <p>
            Authorized access only. Every evidence operation is cryptographically signed and logged.
          </p>
        </div>
      </div>
    </div>
  );
}
