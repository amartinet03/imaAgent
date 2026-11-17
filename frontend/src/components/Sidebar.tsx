import type { FC } from 'react';
import { LayoutDashboard, PlusCircle, Radio, Settings, LogOut } from 'lucide-react';
import { clearAuthToken, getCurrentUser } from '../api/client';

interface SidebarProps {
  currentView: string;
  onNavigate: (view: string) => void;
}

export const Sidebar: FC<SidebarProps> = ({ currentView, onNavigate }) => {
  const user = getCurrentUser();

  const handleLogout = () => {
    clearAuthToken();
    onNavigate('login');
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'nueva_licitacion', label: 'Nueva Licitación', icon: PlusCircle },
    { id: 'radar', label: 'Radar de Licitaciones', icon: Radio },
    { id: 'configuracion', label: 'Configuración', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-[#0F172A] text-slate-100 flex flex-col justify-between p-5 shrink-0 h-full border-r border-slate-800 shadow-xl select-none overflow-hidden">
      <div>
        {/* Brand / Logo */}
        <div className="mb-8">
          <div className="flex items-baseline space-x-1">
            <span className="text-4xl font-black tracking-tight text-white">
              <span className="text-lime-400">i</span>ma
            </span>
          </div>
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider mt-0.5">
            SI | Argentina HOLDAS Latam
          </div>
        </div>

        {/* Navigation */}
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30 font-semibold'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                }`}
              >
                <Icon size={18} className={isActive ? 'text-white' : 'text-slate-400'} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* User profile & footer */}
      <div className="pt-4 border-t border-slate-800/80 space-y-3 shrink-0">
        <div className="flex items-center justify-between text-xs px-1">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center font-bold text-white text-xs shrink-0 shadow-md">
              {user.slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="font-semibold text-slate-200 leading-none truncate">{user}</div>
              <div className="text-[10px] text-emerald-400 font-medium mt-1 flex items-center space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
                <span>En línea</span>
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Cerrar Sesión"
            className="text-slate-400 hover:text-rose-400 p-2 rounded-xl hover:bg-slate-800 transition-colors cursor-pointer shrink-0"
          >
            <LogOut size={16} />
          </button>
        </div>

        <div className="text-[11px] text-slate-500 leading-tight">
          IMA Servicios Industriales<br />
          Plataforma Automática Cloud
        </div>
      </div>
    </aside>
  );
};
