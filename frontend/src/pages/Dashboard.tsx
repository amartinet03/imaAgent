import { useEffect, useState, type FC } from 'react';
import { api } from '../api/client';
import { ConfirmModal } from '../components/ConfirmModal';
import { useToast } from '../components/Toast';
import { formatArgentinaDate } from '../utils/date';
import {
  FileText,
  RotateCw,
  CheckCircle2,
  FolderOpen,
  Trash2,
  Radio,
  ExternalLink,
  Plus,
  AlertTriangle,
  X,
  Sparkles
} from 'lucide-react';

interface Tender {
  id: number;
  name: string;
  status: string;
  progress: number;
  progress_msg?: string;
  created_at: string;
}

interface Stats {
  total: number;
  procesando: number;
  completadas: number;
  nuevas_esta_semana: number;
}

interface Opportunity {
  id: number;
  portal_name: string;
  title: string;
  url?: string;
  matched_keywords?: string;
  snippet?: string;
  status: string;
}

interface DashboardProps {
  onSelectTender: (id: number) => void;
  onNavigate: (view: string) => void;
}

export const Dashboard: FC<DashboardProps> = ({ onSelectTender, onNavigate }) => {
  const { showToast } = useToast();
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [stats, setStats] = useState<Stats>({ total: 0, procesando: 0, completadas: 0, nuevas_esta_semana: 0 });
  const [pendingOpps, setPendingOpps] = useState<Opportunity[]>([]);
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null);
  const [tenderToDelete, setTenderToDelete] = useState<Tender | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const fetchData = async () => {
    try {
      const [tList, tStats, opps] = await Promise.all([
        api.getTenders(),
        api.getStats(),
        api.getPendingOpportunities(),
      ]);
      setTenders(tList);
      setStats(tStats);
      setPendingOpps(opps);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Polling automático cada 3s si hay licitaciones en proceso
  useEffect(() => {
    const hasProcessing = tenders.some((t) => t.status === 'PROCESANDO');
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      fetchData();
    }, 3000);

    return () => clearInterval(interval);
  }, [tenders]);

  const confirmDeleteTender = async () => {
    if (!tenderToDelete) return;
    try {
      setDeletingId(tenderToDelete.id);
      await api.deleteTender(tenderToDelete.id);
      showToast(`Licitación "${tenderToDelete.name}" eliminada con éxito.`, 'success');
      setTenderToDelete(null);
      await fetchData();
    } catch (err: any) {
      showToast(err.message || 'Error al eliminar licitación.', 'error');
    } finally {
      setDeletingId(null);
    }
  };

  const handleApproveOpp = async (oppId: number) => {
    try {
      const res = await api.approveOpportunity(oppId);
      setSelectedOpp(null);
      showToast('¡Oportunidad aprobada! Se inició El Show en segundo plano.', 'success');
      await fetchData();
      if (res.tender_id) {
        onSelectTender(res.tender_id);
      }
    } catch (err: any) {
      showToast(err.message || 'Error al aprobar oportunidad.', 'error');
    }
  };

  const handleRejectOpp = async (oppId: number) => {
    try {
      await api.rejectOpportunity(oppId);
      setSelectedOpp(null);
      showToast('Oportunidad descartada.', 'info');
      await fetchData();
    } catch (err: any) {
      showToast(err.message || 'Error al descartar.', 'error');
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETADO':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 size={12} className="mr-1 text-emerald-600" />
            Completado
          </span>
        );
      case 'PROCESANDO':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200 animate-pulse">
            <RotateCw size={12} className="mr-1 text-blue-600 animate-spin" />
            Procesando
          </span>
        );
      case 'ERROR':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            <AlertTriangle size={12} className="mr-1 text-rose-600" />
            Error
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            Pendiente
          </span>
        );
    }
  };

  const firstOpp = pendingOpps.length > 0 ? pendingOpps[0] : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">
          Dashboard de Licitaciones
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Monitoreo automático de nuevas oportunidades y estado de tus licitaciones.
        </p>
      </div>

      {/* 3 Top Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Licitaciones Totales
            </div>
            <div className="text-3xl font-black text-slate-800 mt-1">
              {stats.total}
            </div>
            <div className="text-xs font-medium text-emerald-600 mt-1">
              {stats.nuevas_esta_semana > 0
                ? `+${stats.nuevas_esta_semana} esta semana`
                : 'Sin nuevas esta semana'}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center text-xl font-bold">
            <FileText size={24} />
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
              En Proceso
            </div>
            <div className="text-3xl font-black text-slate-800 mt-1">
              {stats.procesando}
            </div>
            <div className="text-xs font-medium text-blue-600 mt-1">
              {stats.total > 0
                ? `${Math.round((stats.procesando / stats.total) * 100)}% del total`
                : '0% del total'}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center text-xl font-bold">
            <RotateCw size={24} className={stats.procesando > 0 ? 'animate-spin' : ''} />
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Completadas
            </div>
            <div className="text-3xl font-black text-slate-800 mt-1">
              {stats.completadas}
            </div>
            <div className="text-xs font-medium text-emerald-600 mt-1">
              {stats.total > 0
                ? `${Math.round((stats.completadas / stats.total) * 100)}% del total`
                : '0% del total'}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center text-xl font-bold">
            <CheckCircle2 size={24} />
          </div>
        </div>
      </div>

      {/* RADAR DE LICITACIONES PENDIENTES BANNER */}
      {firstOpp && (
        <div className="bg-gradient-to-r from-slate-900 to-slate-800 border-l-4 border-blue-600 rounded-xl p-4 shadow-lg text-white">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2 text-blue-400 font-bold text-sm tracking-wide">
                <Radio size={16} className="animate-pulse" />
                <span>RADAR DE LICITACIONES: {pendingOpps.length} OPORTUNIDAD(ES) DETECTADA(S) EN LA WEB</span>
              </div>
              <div className="text-sm text-slate-200 font-normal">
                Nueva licitación encontrada en <span className="font-semibold text-white">{firstOpp.portal_name}</span>:{' '}
                <span className="italic">"{firstOpp.title.slice(0, 80)}..."</span>
              </div>
              <div className="text-xs text-slate-400">
                Coincidencia con: <span className="text-blue-300 font-mono">'{firstOpp.matched_keywords}'</span>
              </div>
            </div>
            <div className="flex items-center space-x-2 shrink-0">
              <button
                onClick={() => setSelectedOpp(firstOpp)}
                className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-3.5 py-2 rounded-lg flex items-center space-x-1.5 transition-colors cursor-pointer shadow-md"
              >
                <span>🚨 Revisar Oportunidad</span>
              </button>
              <button
                onClick={() => onNavigate('radar')}
                className="bg-slate-700/80 hover:bg-slate-700 text-slate-200 font-medium text-xs px-3.5 py-2 rounded-lg flex items-center space-x-1.5 transition-colors cursor-pointer"
                title="Ir al Radar de Licitaciones"
              >
                <Radio size={13} className="text-blue-400" />
                <span>Radar de Licitaciones</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table Section Header */}
      <div className="flex items-center justify-between pt-2">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Estado de tus licitaciones</h2>
          <p className="text-xs text-slate-500">Revisa el estado actual o crea una nueva manualmente.</p>
        </div>
        <button
          onClick={() => onNavigate('nueva_licitacion')}
          className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-4 py-2.5 rounded-xl flex items-center space-x-1.5 transition-all shadow-md shadow-blue-600/20 cursor-pointer"
        >
          <Plus size={16} />
          <span>Nueva Licitación</span>
        </button>
      </div>

      {/* Tenders Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-5">Cliente / Proyecto</th>
                <th className="py-3 px-4 text-center">Estado</th>
                <th className="py-3 px-4 text-center">Última Actualización</th>
                <th className="py-3 px-4 text-center">Progreso</th>
                <th className="py-3 px-5 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-400">
                    <RotateCw size={24} className="animate-spin mx-auto mb-2 text-blue-500" />
                    Cargando licitaciones...
                  </td>
                </tr>
              ) : tenders.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-400 text-sm">
                    No hay licitaciones registradas todavía. Crea la primera con el botón de arriba.
                  </td>
                </tr>
              ) : (
                tenders.map((tender) => {
                  const isProcessing = tender.status === 'PROCESANDO';
                  const isError = tender.status === 'ERROR';
                  const pct =
                    tender.progress !== undefined && tender.progress !== null
                      ? tender.progress
                      : tender.status === 'COMPLETADO'
                      ? 100
                      : isProcessing
                      ? 45
                      : 0;

                  return (
                    <tr key={tender.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-4 px-5">
                        <div className="flex items-center space-x-3">
                          <div className="w-9 h-9 rounded-xl border border-slate-200 bg-slate-100 flex items-center justify-center text-base shrink-0">
                            🏢
                          </div>
                          <div>
                            <div className="font-semibold text-slate-800 leading-tight">
                              {tender.name}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-4 text-center">
                        {renderStatusBadge(tender.status)}
                      </td>

                      <td className="py-4 px-4 text-center text-xs text-slate-600 font-medium whitespace-nowrap">
                        {formatArgentinaDate(tender.created_at)}
                      </td>

                      <td className="py-4 px-4 text-center min-w-[160px]">
                        <div className="w-full">
                          <div className="flex justify-between text-[11px] font-semibold text-slate-500 mb-1">
                            <span>{pct}%</span>
                            {isProcessing && (
                              <span className="text-blue-600 animate-pulse text-[10px]">
                                {tender.progress_msg || 'Procesando...'}
                              </span>
                            )}
                          </div>
                          <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200/60">
                            <div
                              className={`h-full transition-all duration-500 rounded-full ${
                                isError
                                  ? 'bg-rose-500'
                                  : tender.status === 'COMPLETADO'
                                  ? 'bg-emerald-500'
                                  : 'bg-blue-600'
                              }`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-5 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => onSelectTender(tender.id)}
                            disabled={isError || isProcessing}
                            title={isError ? 'Falló el análisis' : isProcessing ? 'En progreso' : 'Abrir detalle'}
                            className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                          >
                            <FolderOpen size={14} />
                            <span>Abrir</span>
                          </button>

                          <button
                            onClick={() => setTenderToDelete(tender)}
                            disabled={isProcessing || deletingId === tender.id}
                            title="Eliminar licitación"
                            className="inline-flex items-center px-2 py-1.5 rounded-lg text-xs font-semibold bg-rose-50 text-rose-600 hover:bg-rose-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* OPPORTUNITY CONFIRMATION MODAL */}
      {selectedOpp && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">
                  🏢 {selectedOpp.portal_name}
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-1 leading-snug">
                  {selectedOpp.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedOpp(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            {selectedOpp.snippet && (
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 leading-relaxed max-h-32 overflow-y-auto">
                {selectedOpp.snippet}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-slate-50/80 p-3 rounded-xl border border-slate-200/80">
              <div className="min-w-0">
                <span className="text-slate-400 block font-medium">🎯 Palabras Clave:</span>
                <span className="font-mono font-semibold text-slate-800 break-words">
                  {selectedOpp.matched_keywords || 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block font-medium">🌐 Enlace Oficial:</span>
                {selectedOpp.url ? (
                  <a
                    href={selectedOpp.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline flex items-center space-x-1 font-semibold"
                  >
                    <span>Ver publicación</span>
                    <ExternalLink size={12} />
                  </a>
                ) : (
                  <span className="text-slate-400">No provisto</span>
                )}
              </div>
            </div>

            <div className="border-t border-slate-100 pt-3">
              <p className="text-xs font-semibold text-slate-700 mb-3">
                ¿Deseas confirmar esta licitación y comenzar el análisis integral inteligente (
                <strong>"El Show"</strong>)?
              </p>
              <div className="flex items-center justify-end space-x-2">
                <button
                  onClick={() => handleRejectOpp(selectedOpp.id)}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
                >
                  ❌ Descartar
                </button>
                <button
                  onClick={() => {
                    setSelectedOpp(null);
                    onNavigate('radar');
                  }}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors cursor-pointer flex items-center space-x-1"
                  title="Ver todas las oportunidades en el Radar"
                >
                  <span>📡 Ver Todas</span>
                </button>
                <button
                  onClick={() => handleApproveOpp(selectedOpp.id)}
                  className="px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 rounded-xl flex items-center space-x-1.5 shadow-md shadow-blue-600/30 transition-all cursor-pointer"
                >
                  <Sparkles size={14} />
                  <span>🚀 ¡Sí, Iniciar Show!</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CONFIRMATION MODAL FOR DELETING TENDER */}
      <ConfirmModal
        isOpen={!!tenderToDelete}
        title="Eliminar Licitación Definitivamente"
        message={`¿Estás seguro de que deseas eliminar permanentemente la licitación "${tenderToDelete?.name}" y todos sus documentos asociados? Esta acción no se puede deshacer.`}
        confirmText="Sí, Eliminar Licitación"
        cancelText="Cancelar"
        type="danger"
        loading={deletingId !== null}
        onConfirm={confirmDeleteTender}
        onCancel={() => setTenderToDelete(null)}
      />
    </div>
  );
};
