import { useEffect, useState, type FC, type FormEvent } from 'react';
import { api } from '../api/client';
import { ConfirmModal } from '../components/ConfirmModal';
import { useToast } from '../components/Toast';
import {
  Radio,
  Globe,
  Tag,
  RotateCw,
  ExternalLink,
  Plus,
  Trash2,
  CheckCircle2,
  Sparkles,
  Search,
  Check,
  Mail,
  Clock,
  ShieldCheck
} from 'lucide-react';

interface RadarPageProps {
  onTenderCreated?: (id: number) => void;
}

const COMMON_KEYWORD_SUGGESTIONS = [
  'turbina',
  'gasoducto',
  'valvulas',
  'bombas',
  'transformadores',
  'instrumentacion',
  'subestacion',
  'refrigeracion',
  'aislamiento',
  'calderas'
];

export const RadarPage: FC<RadarPageProps> = ({ onTenderCreated }) => {
  const { showToast } = useToast();
  // Tab order requested: 1) Oportunidades, 2) Sitios Web, 3) Palabras Clave
  const [activeTab, setActiveTab] = useState<'opportunities' | 'portals' | 'keywords'>('opportunities');

  // Deletion modals
  const [oppToDelete, setOppToDelete] = useState<any | null>(null);
  const [portalToDelete, setPortalToDelete] = useState<any | null>(null);
  const [keywordToDelete, setKeywordToDelete] = useState<any | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Opportunities state
  const [opps, setOpps] = useState<any[]>([]);
  const [oppFilter, setOppFilter] = useState<'ALL' | 'PENDIENTE' | 'APROBADA' | 'DESCARTADA'>('PENDIENTE');
  const [scanning, setScanning] = useState(false);
  const [sendingDigest, setSendingDigest] = useState(false);

  // Portals state
  const [portals, setPortals] = useState<any[]>([]);
  const [newPortalName, setNewPortalName] = useState('');
  const [newPortalUrl, setNewPortalUrl] = useState('');
  const [newPortalFreq, setNewPortalFreq] = useState('Diaria');

  // Keywords state
  const [keywords, setKeywords] = useState<any[]>([]);
  const [newKeyword, setNewKeyword] = useState('');
  const [keywordSearch, setKeywordSearch] = useState('');

  const fetchOpps = async () => {
    try {
      const data = await api.getOpportunities();
      setOpps(data);
    } catch (e) {
      console.error('Error fetching opportunities:', e);
    }
  };

  const fetchPortals = async () => {
    try {
      const data = await api.getPortals();
      setPortals(data);
    } catch (e) {
      console.error('Error fetching portals:', e);
    }
  };

  const fetchKeywords = async () => {
    try {
      const data = await api.getKeywords();
      setKeywords(data);
    } catch (e) {
      console.error('Error fetching keywords:', e);
    }
  };

  useEffect(() => {
    fetchOpps();
    fetchPortals();
    fetchKeywords();
  }, []);

  // Actions for Opportunities
  const handleForceScan = async () => {
    setScanning(true);
    try {
      await api.triggerScan();
      showToast('¡Escaneo de portales web iniciado en segundo plano!', 'info');
      // Wait a moment then refresh
      setTimeout(() => {
        fetchOpps();
        fetchPortals();
      }, 3000);
    } catch (err: any) {
      showToast(err.message || 'Error al iniciar escaneo', 'error');
    } finally {
      setScanning(false);
    }
  };

  const handleSendWeeklyDigest = async () => {
    setSendingDigest(true);
    try {
      const res = await api.sendWeeklyDigest();
      if (res.sent) {
        showToast(`¡Resumen semanal enviado a ${res.recipient} (${res.pending_count} licitaciones)!`, 'success');
      } else {
        showToast(res.reason || 'No se envió el resumen semanal.', 'info');
      }
    } catch (err: any) {
      showToast(err.message || 'Error al enviar resumen semanal', 'error');
    } finally {
      setSendingDigest(false);
    }
  };

  const handleApproveOpp = async (id: number) => {
    try {
      const res = await api.approveOpportunity(id);
      showToast(res.message || '¡Oportunidad aprobada! Se inició el análisis inteligente.', 'success');
      await fetchOpps();
      if (res.tender_id && onTenderCreated) {
        onTenderCreated(res.tender_id);
      }
    } catch (err: any) {
      showToast(err.message || 'Error al aprobar', 'error');
    }
  };

  const handleRejectOpp = async (id: number) => {
    try {
      await api.rejectOpportunity(id);
      showToast('Oportunidad descartada permanentemente. No volverá a aparecer en nuevos análisis.', 'info');
      await fetchOpps();
    } catch (err: any) {
      showToast(err.message || 'Error al descartar', 'error');
    }
  };

  const confirmDeleteOpp = async () => {
    if (!oppToDelete) return;
    setIsDeleting(true);
    try {
      await api.deleteOpportunity(oppToDelete.id);
      showToast('Oportunidad eliminada permanentemente del radar.', 'success');
      setOppToDelete(null);
      await fetchOpps();
    } catch (err: any) {
      showToast(err.message || 'Error al eliminar oportunidad', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  // Actions for Portals
  const handleAddPortal = async (e: FormEvent) => {
    e.preventDefault();
    if (!newPortalName.trim() || !newPortalUrl.trim()) return;
    try {
      await api.createPortal({ name: newPortalName, url: newPortalUrl, frequency: newPortalFreq });
      setNewPortalName('');
      setNewPortalUrl('');
      showToast('Portal guardado exitosamente en el radar.', 'success');
      await fetchPortals();
    } catch (err: any) {
      showToast(err.message || 'Error al agregar portal', 'error');
    }
  };

  const handleTogglePortal = async (id: number) => {
    try {
      await api.togglePortal(id);
      showToast('Estado del portal actualizado.', 'info');
      await fetchPortals();
    } catch (err: any) {
      showToast(err.message || 'Error al cambiar estado', 'error');
    }
  };

  const confirmDeletePortal = async () => {
    if (!portalToDelete) return;
    setIsDeleting(true);
    try {
      await api.deletePortal(portalToDelete.id);
      showToast(`Portal "${portalToDelete.name}" eliminado del radar.`, 'success');
      setPortalToDelete(null);
      await fetchPortals();
    } catch (err: any) {
      showToast(err.message || 'Error al eliminar portal', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  // Actions for Keywords
  const handleAddKeyword = async (e?: FormEvent, customKw?: string) => {
    if (e) e.preventDefault();
    const kw = (customKw || newKeyword).trim();
    if (!kw) return;
    try {
      await api.createKeyword(kw);
      if (!customKw) setNewKeyword('');
      showToast(`Palabra clave "${kw}" agregada correctamente.`, 'success');
      await fetchKeywords();
    } catch (err: any) {
      showToast(err.message || 'Error al agregar palabra clave', 'error');
    }
  };

  const confirmDeleteKeyword = async () => {
    if (!keywordToDelete) return;
    setIsDeleting(true);
    try {
      await api.deleteKeyword(keywordToDelete.id);
      showToast(`Palabra clave "${keywordToDelete.keyword}" eliminada.`, 'success');
      setKeywordToDelete(null);
      await fetchKeywords();
    } catch (err: any) {
      showToast(err.message || 'Error al eliminar', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  // Counters & filters
  const pendingOppsCount = opps.filter((o) => o.status === 'PENDIENTE').length;
  const approvedOppsCount = opps.filter((o) => o.status === 'APROBADA').length;
  const discardedOppsCount = opps.filter((o) => o.status === 'DESCARTADA').length;

  const filteredOpps = opps.filter((o) => {
    if (oppFilter === 'ALL') return true;
    return o.status === oppFilter;
  });

  const filteredKeywords = keywords.filter((k) =>
    k.keyword.toLowerCase().includes(keywordSearch.toLowerCase().trim())
  );

  const TABS = [
    {
      id: 'opportunities',
      label: 'Oportunidades Detectadas',
      icon: Radio,
      count: pendingOppsCount,
      highlight: pendingOppsCount > 0
    },
    {
      id: 'portals',
      label: 'Sitios Web Monitoreados',
      icon: Globe,
      count: portals.length
    },
    {
      id: 'keywords',
      label: 'Palabras Clave de Filtrado',
      icon: Tag,
      count: keywords.length
    }
  ];

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <span>Radar de Licitaciones</span>
            <span className="text-xl">📡</span>
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Monitoreo autónomo de portales oficiales, detección inteligente de oportunidades y resumen semanal por correo los viernes.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            disabled={sendingDigest}
            onClick={handleSendWeeklyDigest}
            className="flex items-center space-x-2 px-3.5 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold transition-all shadow-sm cursor-pointer disabled:opacity-50"
            title="Enviar o verificar resumen semanal a tu correo oficial"
          >
            {sendingDigest ? (
              <RotateCw size={14} className="animate-spin text-blue-600" />
            ) : (
              <Mail size={14} className="text-blue-600" />
            )}
            <span>Enviar Reporte Viernes</span>
          </button>

          <button
            type="button"
            disabled={scanning}
            onClick={handleForceScan}
            className="flex items-center space-x-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-blue-600/20 cursor-pointer disabled:opacity-50"
          >
            <RotateCw size={14} className={scanning ? 'animate-spin' : ''} />
            <span>{scanning ? 'Escaneando Portales...' : 'Escanear Ahora ⚡'}</span>
          </button>
        </div>
      </div>

      {/* Modern Status Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-slate-900 to-slate-900 text-white rounded-2xl p-4 border border-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-500/20 text-blue-400 border border-blue-500/30 flex items-center justify-center shrink-0">
            <Radio size={18} className="animate-pulse" />
          </div>
          <div>
            <div className="font-bold text-slate-100 flex items-center gap-2">
              <span>Búsqueda periódica continua activa</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-ping"></span>
            </div>
            <div className="text-slate-400 text-[11px] mt-0.5">
              Las licitaciones se guardan aquí hasta que decidas analizarlas o descartarlas. Si las descartas, quedan registradas para no volver a repetirse.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto bg-slate-800/80 px-3 py-1.5 rounded-xl border border-slate-700/80 shrink-0">
          <Clock size={13} className="text-amber-400" />
          <span className="text-[11px] text-slate-300">
            Resumen semanal: <strong>Viernes</strong>
          </span>
        </div>
      </div>

      {/* Tabs Bar */}
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
              {tab.count !== undefined && (
                <span
                  className={`text-[11px] px-2 py-0.5 rounded-full font-bold transition-colors ${
                    isActive
                      ? tab.highlight
                        ? 'bg-blue-600 text-white'
                        : 'bg-blue-50 text-blue-600'
                      : tab.highlight
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-slate-300/60 text-slate-700'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: OPORTUNIDADES DETECTADAS (Primera instancia solicitada) */}
      {/* ========================================================================= */}
      {activeTab === 'opportunities' && (
        <div className="space-y-4">
          {/* Sub-filtros por estado */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3.5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                type="button"
                onClick={() => setOppFilter('PENDIENTE')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  oppFilter === 'PENDIENTE'
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200/80'
                }`}
              >
                Pendientes ({pendingOppsCount})
              </button>
              <button
                type="button"
                onClick={() => setOppFilter('APROBADA')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  oppFilter === 'APROBADA'
                    ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-600/30'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200/80'
                }`}
              >
                Aprobadas ({approvedOppsCount})
              </button>
              <button
                type="button"
                onClick={() => setOppFilter('DESCARTADA')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  oppFilter === 'DESCARTADA'
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200/80'
                }`}
              >
                Descartadas ({discardedOppsCount})
              </button>
              <button
                type="button"
                onClick={() => setOppFilter('ALL')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  oppFilter === 'ALL'
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200/80'
                }`}
              >
                Todas ({opps.length})
              </button>
            </div>

            <div className="text-xs text-slate-400 font-medium self-end sm:self-auto">
              Mostrando {filteredOpps.length} resultado(s)
            </div>
          </div>

          {/* Listado de oportunidades */}
          {filteredOpps.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
              <Radio size={40} className="mx-auto text-slate-300 mb-3" />
              <h3 className="text-base font-bold text-slate-800">
                No hay oportunidades {oppFilter !== 'ALL' ? `en estado "${oppFilter.toLowerCase()}"` : 'detectadas'}
              </h3>
              <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                {oppFilter === 'PENDIENTE'
                  ? 'El radar continúa rastreando los portales oficiales automáticamente. Puedes forzar un escaneo ahora haciendo clic en el botón superior.'
                  : 'No se encontraron registros bajo este filtro.'}
              </p>
              {oppFilter === 'PENDIENTE' && (
                <button
                  type="button"
                  disabled={scanning}
                  onClick={handleForceScan}
                  className="mt-4 px-4 py-2 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-xl text-xs font-bold transition-all cursor-pointer inline-flex items-center gap-1.5 border border-blue-200"
                >
                  <RotateCw size={13} className={scanning ? 'animate-spin' : ''} />
                  <span>Escanear Portales Ahora</span>
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredOpps.map((opp) => {
                const isPending = opp.status === 'PENDIENTE';
                const isApproved = opp.status === 'APROBADA';
                const isDiscarded = opp.status === 'DESCARTADA';

                return (
                  <div
                    key={opp.id}
                    className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:border-slate-300 transition-all space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                            {opp.portal_name || 'Portal Oficial'}
                          </span>

                          {isPending && (
                            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                              Pendiente de Revisión
                            </span>
                          )}
                          {isApproved && (
                            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                              <CheckCircle2 size={11} />
                              <span>Aprobada / Licitación #{opp.tender_id}</span>
                            </span>
                          )}
                          {isDiscarded && (
                            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200">
                              Descartada (Tombstoned)
                            </span>
                          )}
                        </div>

                        <h3 className="text-base font-bold text-slate-900 leading-snug">
                          {opp.title}
                        </h3>

                        {opp.snippet && (
                          <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                            {opp.snippet}
                          </p>
                        )}
                      </div>

                      {/* Botón de enlace externo */}
                      {opp.url && (
                        <a
                          href={opp.url}
                          target="_blank"
                          rel="noreferrer"
                          className="shrink-0 text-slate-400 hover:text-blue-600 p-2 rounded-xl hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-200 self-start"
                          title="Abrir pliego en portal oficial"
                        >
                          <ExternalLink size={16} />
                        </a>
                      )}
                    </div>

                    {/* Palabras clave coincidentes & Acciones */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-100 text-xs">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-slate-400 text-[11px] font-medium">Coincidencias:</span>
                        {opp.matched_keywords ? (
                          opp.matched_keywords.split(',').map((kw: string, i: number) => (
                            <span
                              key={i}
                              className="text-[11px] font-semibold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md border border-slate-200"
                            >
                              {kw.trim()}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-400 text-[11px]">General</span>
                        )}
                      </div>

                      {/* Botones de acción */}
                      <div className="flex items-center gap-2 self-end sm:self-auto">
                        {isPending && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleRejectOpp(opp.id)}
                              className="px-3 py-1.5 rounded-xl border border-slate-200 text-slate-600 hover:text-rose-600 hover:bg-rose-50 text-xs font-semibold transition-all cursor-pointer"
                              title="Descartar para que no vuelva a aparecer en futuros escaneos"
                            >
                              Descartar
                            </button>
                            <button
                              type="button"
                              onClick={() => handleApproveOpp(opp.id)}
                              className="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-sm shadow-blue-600/25 cursor-pointer flex items-center gap-1.5"
                            >
                              <Sparkles size={13} />
                              <span>Analizar con IA 🚀</span>
                            </button>
                          </>
                        )}

                        <button
                          type="button"
                          onClick={() => setOppToDelete(opp)}
                          className="p-1.5 rounded-lg text-slate-300 hover:text-rose-500 hover:bg-rose-50 transition-colors cursor-pointer"
                          title="Eliminar registro"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: SITIOS WEB MONITOREADOS */}
      {/* ========================================================================= */}
      {activeTab === 'portals' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Formulario Agregar Portal (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            <form onSubmit={handleAddPortal} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
              <div className="flex items-center space-x-2 text-slate-800 font-bold text-sm border-b border-slate-100 pb-3">
                <Plus size={16} className="text-blue-600" />
                <span>Agregar Nueva Página Web al Radar</span>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Nombre de la Entidad / Portal *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej: AySA / Enarsa / YPF / Nucleoeléctrica"
                  value={newPortalName}
                  onChange={(e) => setNewPortalName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Frecuencia de Chequeo
                </label>
                <select
                  value={newPortalFreq}
                  onChange={(e) => setNewPortalFreq(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all cursor-pointer"
                >
                  <option value="Diaria">Diaria (Recomendada)</option>
                  <option value="Cada 12 Horas">Cada 12 Horas</option>
                  <option value="Semanal">Semanal</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  URL de Licitaciones Vigentes *
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://www.entidad.gob.ar/licitaciones"
                  value={newPortalUrl}
                  onChange={(e) => setNewPortalUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-3 px-4 rounded-xl shadow-md shadow-blue-600/20 transition-all cursor-pointer flex items-center justify-center space-x-2"
              >
                <span>Guardar Portal en el Radar</span>
                <Sparkles size={14} />
              </button>
            </form>

            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-xs text-slate-600 space-y-1.5">
              <div className="font-bold text-slate-800 flex items-center gap-1.5">
                <Globe size={14} className="text-blue-500" />
                <span>Rastreo Proactivo Inteligente</span>
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                El agente inspecciona el código HTML de cada portal oficial, descartando licitaciones de años pasados y verificando que cumplan con las palabras clave activas antes de alertarte.
              </p>
            </div>
          </div>

          {/* Listado de Portales (7 cols) */}
          <div className="lg:col-span-7">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                  <Globe size={16} className="text-blue-600" />
                  <span>Listado de Portales para Extracción ({portals.length})</span>
                </div>
                <span className="text-xs text-slate-500 font-medium">
                  {portals.filter((p) => !!p.active).length} activos
                </span>
              </div>

              {portals.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs">
                  Aún no has agregado portales al radar. Utiliza el formulario de la izquierda.
                </div>
              ) : (
                <div className="space-y-3">
                  {portals.map((p) => {
                    const isActive = !!p.active;
                    return (
                      <div
                        key={p.id}
                        className={`p-4 rounded-xl border transition-all space-y-2 ${
                          isActive
                            ? 'bg-slate-50/70 border-slate-200 hover:border-slate-300'
                            : 'bg-slate-100/50 border-slate-200 opacity-60'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2.5 min-w-0 pr-2">
                            <span
                              className={`w-2 h-2 rounded-full shrink-0 ${
                                isActive ? 'bg-emerald-500' : 'bg-slate-400'
                              }`}
                            />
                            <div className="min-w-0">
                              <span className="font-bold text-xs text-slate-800 block truncate">
                                {p.name}
                              </span>
                              <div className="flex items-center gap-2 mt-0.5">
                                <a
                                  href={p.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-[11px] text-blue-600 hover:underline flex items-center gap-1 truncate max-w-xs"
                                >
                                  <span className="truncate">{p.url}</span>
                                  <ExternalLink size={10} className="shrink-0" />
                                </a>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center space-x-2 shrink-0">
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-200/80 text-slate-600">
                              {p.frequency || 'Diaria'}
                            </span>
                            <button
                              type="button"
                              onClick={() => handleTogglePortal(p.id)}
                              className={`text-[11px] font-bold px-2.5 py-1 rounded-lg transition-colors cursor-pointer ${
                                isActive
                                  ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'
                                  : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                              }`}
                            >
                              {isActive ? 'Activo' : 'En Pausa'}
                            </button>
                            <button
                              type="button"
                              onClick={() => setPortalToDelete(p)}
                              className="text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
                              title="Eliminar portal del radar"
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-200/60 pt-2">
                          <div className="flex items-center gap-1">
                            <Clock size={12} />
                            <span>Último rastreo: {p.last_scanned ? p.last_scanned : 'Aún no escaneado'}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: PALABRAS CLAVE DE FILTRADO */}
      {/* ========================================================================= */}
      {activeTab === 'keywords' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Formulario & Sugerencias Rápidas (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            <form onSubmit={(e) => handleAddKeyword(e)} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
              <div className="flex items-center space-x-2 text-slate-800 font-bold text-sm border-b border-slate-100 pb-3">
                <Tag size={16} className="text-blue-600" />
                <span>Agregar Palabra Clave de Filtrado</span>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Término o Especialidad Técnica *
                </label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    placeholder="Ej: piping, desgasificador, parada de planta..."
                    value={newKeyword}
                    onChange={(e) => setNewKeyword(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all pl-9"
                  />
                  <Tag size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                </div>
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-3 px-4 rounded-xl shadow-md shadow-blue-600/20 transition-all cursor-pointer flex items-center justify-center space-x-2"
              >
                <span>Incorporar Palabra Clave</span>
                <Plus size={14} />
              </button>
            </form>

            {/* Quick Industry Suggestions */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Sparkles size={14} className="text-amber-500" />
                <span>Sugerencias del Rubro Industrial</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Haz clic sobre cualquiera para incorporarla rápidamente a tus filtros activos:
              </p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {COMMON_KEYWORD_SUGGESTIONS.map((item) => {
                  const alreadyAdded = keywords.some((k) => k.keyword.toLowerCase() === item.toLowerCase());
                  return (
                    <button
                      key={item}
                      type="button"
                      disabled={alreadyAdded}
                      onClick={() => handleAddKeyword(undefined, item)}
                      className={`text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition-all cursor-pointer flex items-center gap-1 ${
                        alreadyAdded
                          ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
                          : 'bg-blue-50/80 text-blue-700 border-blue-200 hover:bg-blue-100'
                      }`}
                    >
                      <span>{item}</span>
                      {alreadyAdded ? <Check size={11} /> : <Plus size={11} />}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-xs text-slate-600 space-y-1.5">
              <div className="font-bold text-slate-800 flex items-center gap-1.5">
                <ShieldCheck size={14} className="text-emerald-600" />
                <span>Protección contra Falsos Positivos</span>
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                El motor aplica límites de palabra exactos (regex <code>\bpalabra\b</code>). De este modo, por ejemplo, "bomba" no coincidirá erróneamente con "bombacha" o términos irrelevantes.
              </p>
            </div>
          </div>

          {/* Listado de Palabras Clave Activas (7 cols) */}
          <div className="lg:col-span-7">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                  <Tag size={16} className="text-blue-600" />
                  <span>Palabras Clave Activas ({keywords.length})</span>
                </div>

                <div className="relative">
                  <input
                    type="text"
                    placeholder="Buscar palabra..."
                    value={keywordSearch}
                    onChange={(e) => setKeywordSearch(e.target.value)}
                    className="w-48 pl-7 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:bg-white"
                  />
                  <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                </div>
              </div>

              {keywords.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs">
                  No hay palabras clave registradas. El radar requiere al menos una palabra clave para detectar oportunidades oficiales.
                </div>
              ) : filteredKeywords.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs">
                  No se encontraron palabras clave que coincidan con "{keywordSearch}".
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {filteredKeywords.map((kw) => (
                    <div
                      key={kw.id}
                      className="flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100/70 border border-slate-200 rounded-xl text-xs text-slate-800 transition-colors group"
                    >
                      <div className="flex items-center space-x-2 truncate pr-2">
                        <Tag size={13} className="text-blue-500 shrink-0" />
                        <span className="font-semibold truncate">{kw.keyword}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setKeywordToDelete(kw)}
                        className="text-slate-300 hover:text-rose-500 p-1 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer shrink-0"
                        title="Eliminar palabra clave"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modals de confirmación de eliminación */}
      <ConfirmModal
        isOpen={!!oppToDelete}
        title="Eliminar Oportunidad del Radar"
        message={`¿Estás seguro de que deseas eliminar permanentemente "${oppToDelete?.title}"? Esta licitación quedará registrada en el sistema de lápidas (tombstones) para no volver a repetirse.`}
        confirmText="Eliminar Permanentemente"
        type="danger"
        loading={isDeleting}
        onConfirm={confirmDeleteOpp}
        onCancel={() => setOppToDelete(null)}
      />

      <ConfirmModal
        isOpen={!!portalToDelete}
        title="Eliminar Portal Monitoreado"
        message={`¿Deseas eliminar "${portalToDelete?.name}" del radar? Dejará de escanearse automáticamente.`}
        confirmText="Eliminar Portal"
        type="danger"
        loading={isDeleting}
        onConfirm={confirmDeletePortal}
        onCancel={() => setPortalToDelete(null)}
      />

      <ConfirmModal
        isOpen={!!keywordToDelete}
        title="Eliminar Palabra Clave"
        message={`¿Deseas eliminar la palabra clave "${keywordToDelete?.keyword}"?`}
        confirmText="Eliminar"
        type="danger"
        loading={isDeleting}
        onConfirm={confirmDeleteKeyword}
        onCancel={() => setKeywordToDelete(null)}
      />
    </div>
  );
};
