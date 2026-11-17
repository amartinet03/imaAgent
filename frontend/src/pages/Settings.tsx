import { useEffect, useState, type FC, type FormEvent } from 'react';
import { api, getCurrentUser } from '../api/client';
import { useToast } from '../components/Toast';
import {
  Cpu,
  Lock,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Check,
  Mail,
  Cloud,
  Briefcase,
  Bot,
  Power
} from 'lucide-react';

interface SettingsProps {
  onTenderCreated?: (id: number) => void;
}

export const Settings: FC<SettingsProps> = () => {
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<'daemon' | 'password'>('daemon');

  // Daemon state
  const [daemonActive, setDaemonActive] = useState(false);
  const [daemonSettings, setDaemonSettings] = useState<any>({ mail: false, sharepoint: false, pipedrive: false, ai: false });

  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordMsg, setPasswordMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchDaemon = async () => {
    try {
      const data = await api.getDaemon();
      setDaemonActive(data.active);
      setDaemonSettings(data.settings || {});
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchDaemon();
  }, []);

  const handleUpdateDaemon = async (updated: any) => {
    try {
      const res = await api.updateDaemon(updated);
      setDaemonActive(res.active);
      setDaemonSettings(res.settings);
      showToast('Configuración del Daemon actualizada.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Error al actualizar automatización', 'error');
    }
  };

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordMsg(null);

    if (newPassword !== confirmPassword) {
      setPasswordMsg({ type: 'error', text: 'Las nuevas contraseñas no coinciden.' });
      return;
    }
    if (newPassword.length < 6) {
      setPasswordMsg({ type: 'error', text: 'La nueva contraseña debe tener al menos 6 caracteres.' });
      return;
    }

    try {
      await api.changePassword({
        username: getCurrentUser(),
        current_password: currentPassword,
        new_password: newPassword
      });
      setPasswordMsg({ type: 'success', text: '¡Contraseña actualizada exitosamente!' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordMsg({ type: 'error', text: err.message || 'Error al cambiar contraseña' });
    }
  };

  const TABS = [
    { id: 'daemon', label: 'Automatización (Daemon)', icon: Cpu, isDaemonActive: daemonActive },
    { id: 'password', label: 'Seguridad & Acceso', icon: Lock },
  ];

  return (
    <div className="w-full space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
          <span>Configuración del Sistema</span>
          <span className="text-xl">⚙️</span>
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Gestión del servicio autónomo en segundo plano (Daemon), integraciones M365/CRM y seguridad de la cuenta.
        </p>
      </div>

      {/* Tabs Navigation */}
      <div className="bg-slate-200/70 p-1.5 rounded-2xl flex flex-wrap gap-1.5 border border-slate-200/80 shadow-inner">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${
                isActive
                  ? 'bg-white text-blue-600 shadow-sm shadow-slate-200'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <Icon size={16} className={isActive ? 'text-blue-600' : 'text-slate-400'} />
              <span>{tab.label}</span>
              {tab.isDaemonActive !== undefined && (
                <span
                  className={`w-2.5 h-2.5 rounded-full transition-all ${
                    tab.isDaemonActive ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50 animate-pulse' : 'bg-slate-400'
                  }`}
                  title={tab.isDaemonActive ? 'Daemon activo' : 'Daemon en pausa'}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: DAEMON DE AUTOMATIZACIÓN */}
      {/* ========================================================================= */}
      {activeTab === 'daemon' && (
        <div className="space-y-6">
          {/* Master Switch Banner */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span
                  className={`w-3 h-3 rounded-full ${
                    daemonActive ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50 animate-pulse' : 'bg-slate-300'
                  }`}
                />
                <h3 className="font-bold text-slate-900 text-base">
                  {daemonActive ? 'Daemon ACTIVO y Monitoreando' : 'Daemon en PAUSA'}
                </h3>
              </div>
              <p className="text-xs text-slate-500">
                Control maestro para escaneos periódicos en segundo plano, lectura de correos entrantes y sincronización en la nube.
              </p>
            </div>

            <button
              onClick={() => handleUpdateDaemon({ active: !daemonActive })}
              className={`flex items-center space-x-2 px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer shrink-0 ${
                daemonActive
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/30'
                  : 'bg-slate-900 hover:bg-slate-800 text-white shadow-md'
              }`}
            >
              <Power size={15} />
              <span>{daemonActive ? 'Detener Daemon' : 'Activar Daemon General'}</span>
            </button>
          </div>

          {/* Feature Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
            {[
              {
                key: 'mail',
                title: 'Monitoreo de Correo (Microsoft 365 Graph)',
                desc: 'Detecta llamados y pedidos de cotización recibidos automáticamente en la bandeja de entrada.',
                icon: Mail,
                color: 'text-blue-500'
              },
              {
                key: 'sharepoint',
                title: 'Sincronización SharePoint / OneDrive',
                desc: 'Sube automáticamente las nuevas revisiones generadas (DOCX y XLSX) al sitio corporativo.',
                icon: Cloud,
                color: 'text-cyan-500'
              },
              {
                key: 'pipedrive',
                title: 'Integración CRM Pipedrive',
                desc: 'Registra los tratos y sincroniza clientes y licitaciones ganadas en el pipeline comercial.',
                icon: Briefcase,
                color: 'text-amber-500'
              },
              {
                key: 'ai',
                title: 'Procesamiento Autónomo con IA',
                desc: 'Dispara "El Show" automáticamente sin confirmación manual ante nuevos avisos detectados.',
                icon: Bot,
                color: 'text-purple-500'
              },
            ].map((item) => {
              const active = !!daemonSettings[item.key];
              const Icon = item.icon;
              return (
                <div
                  key={item.key}
                  className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm flex items-start justify-between gap-4"
                >
                  <div className="flex items-start space-x-3.5">
                    <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0">
                      <Icon size={20} className={item.color} />
                    </div>
                    <div className="space-y-1">
                      <div className="font-bold text-slate-800 text-sm">{item.title}</div>
                      <div className="text-[11px] text-slate-400 leading-relaxed">{item.desc}</div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleUpdateDaemon({ [item.key]: !active })}
                    className={`text-xs font-bold px-3.5 py-1.5 rounded-xl border transition-all cursor-pointer shrink-0 ${
                      active
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100'
                        : 'bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200'
                    }`}
                  >
                    {active ? 'ON' : 'OFF'}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: SEGURIDAD & CONTRASEÑA */}
      {/* ========================================================================= */}
      {activeTab === 'password' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Form (7 cols) */}
          <div className="lg:col-span-7">
            <form onSubmit={handleChangePassword} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
              <div className="flex items-center space-x-2 text-slate-800 font-bold text-sm border-b border-slate-100 pb-3">
                <Lock size={16} className="text-blue-600" />
                <span>Actualizar Contraseña de Acceso</span>
              </div>

              {passwordMsg && (
                <div
                  className={`p-3.5 rounded-xl text-xs flex items-center space-x-2 ${
                    passwordMsg.type === 'success'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : 'bg-rose-50 text-rose-800 border border-rose-200'
                  }`}
                >
                  {passwordMsg.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                  <span>{passwordMsg.text}</span>
                </div>
              )}

              <div className="space-y-3.5 text-xs">
                <div>
                  <label className="block text-slate-600 font-bold mb-1">Contraseña Actual *</label>
                  <input
                    type="password"
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Ingresa tu contraseña actual"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-bold mb-1">Nueva Contraseña (mínimo 6 caracteres) *</label>
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Nueva clave segura"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-bold mb-1">Confirmar Nueva Contraseña *</label>
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repite la nueva contraseña"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-3 px-4 rounded-xl shadow-md shadow-blue-600/20 transition-all cursor-pointer"
              >
                Actualizar Contraseña
              </button>
            </form>
          </div>

          {/* Right Column: Security Info (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-3 text-xs">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                <ShieldCheck size={16} className="text-emerald-600" />
                <span>Seguridad de la Cuenta</span>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl space-y-1 text-slate-600">
                <div className="text-[11px] text-slate-400">Usuario activo</div>
                <div className="font-bold text-slate-800 text-sm font-mono">{getCurrentUser()}</div>
              </div>
              <ul className="space-y-1.5 text-slate-500 text-[11px]">
                <li className="flex items-center gap-1.5">
                  <Check size={13} className="text-emerald-500" />
                  <span>Cifrado de contraseña con salted hash (bcrypt/sha256).</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <Check size={13} className="text-emerald-500" />
                  <span>Sesión con token seguro de navegación.</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <Check size={13} className="text-emerald-500" />
                  <span>Requiere al menos 6 caracteres.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
