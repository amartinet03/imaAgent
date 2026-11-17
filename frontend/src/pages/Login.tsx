import { useState, type FC, type FormEvent } from 'react';
import { api, setAuthToken } from '../api/client';
import { Lock, User, ArrowRight, AlertCircle, ShieldCheck } from 'lucide-react';

interface LoginProps {
  onSuccess: () => void;
}

export const Login: FC<LoginProps> = ({ onSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await api.login({ username, password });
      setAuthToken(res.token, res.username);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Error de autenticación. Verifica tus credenciales.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-800/90 border border-slate-700/80 rounded-2xl p-8 shadow-2xl backdrop-blur-xl">
        <div className="text-center mb-8">
          <div className="inline-flex items-baseline space-x-1 mb-2">
            <span className="text-5xl font-black text-white tracking-tight">
              <span className="text-lime-400">i</span>ma
            </span>
          </div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
            SI | Argentina HOLDAS Latam
          </p>
          <h2 className="text-xl font-bold text-slate-100 mt-4">
            Plataforma Inteligente de Licitaciones
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Ingresa con tu usuario y contraseña institucional
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3.5 bg-rose-500/15 border border-rose-500/30 rounded-xl flex items-center space-x-3 text-rose-300 text-sm">
            <AlertCircle size={18} className="shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Usuario
            </label>
            <div className="relative">
              <User size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                className="w-full bg-slate-900/80 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Contraseña
            </label>
            <div className="relative">
              <Lock size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-900/80 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-4 rounded-xl flex items-center justify-center space-x-2 transition-all shadow-lg shadow-blue-600/30 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {loading ? (
              <span className="text-sm">Iniciando sesión...</span>
            ) : (
              <>
                <span className="text-sm">Ingresar a la Plataforma</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-700/60 flex items-center justify-center space-x-2 text-xs text-slate-400">
          <ShieldCheck size={16} className="text-emerald-400" />
          <span>Acceso seguro protegido con tokens y PostgreSQL</span>
        </div>
      </div>
    </div>
  );
};
