import { useEffect, useState, useRef, type FC, type FormEvent } from 'react';
import { api } from '../api/client';
import { ConfirmModal } from '../components/ConfirmModal';
import { useToast } from '../components/Toast';
import { AdaptiveInfoRow } from '../components/AdaptiveInfoRow';
import { formatArgentinaDate } from '../utils/date';
import {
  ArrowLeft,
  RotateCw,
  Sparkles,
  Download,
  UploadCloud,
  FileText,
  HelpCircle,
  FileCheck,
  Send,
  X,
  History,
  Save,
  CheckCircle2
} from 'lucide-react';

interface TenderDetailProps {
  tenderId: number;
  onBack: () => void;
}

export const TenderDetail: FC<TenderDetailProps> = ({ tenderId, onBack }) => {
  const { showToast } = useToast();
  const [tender, setTender] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'docs' | 'rfi' | 'ot' | 'eco'>('docs');
  const [showReanalyzeConfirm, setShowReanalyzeConfirm] = useState(false);

  // Documents tab state
  const [documents, setDocuments] = useState<any[]>([]);
  const [uploadFiles, setUploadFiles] = useState<FileList | null>(null);
  const [isUploadingDocs, setIsUploadingDocs] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);
  const leftDocsColRef = useRef<HTMLDivElement>(null);
  const [leftDocsHeight, setLeftDocsHeight] = useState<number | undefined>(undefined);

  useEffect(() => {
    if (!leftDocsColRef.current) return;
    const updateHeight = () => {
      if (leftDocsColRef.current && window.innerWidth >= 768) {
        setLeftDocsHeight(Math.round(leftDocsColRef.current.offsetHeight));
      } else {
        setLeftDocsHeight(undefined);
      }
    };
    updateHeight();
    const ro = new ResizeObserver(updateHeight);
    ro.observe(leftDocsColRef.current);
    window.addEventListener('resize', updateHeight);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', updateHeight);
    };
  }, [activeTab]);

  // RFI tab state
  const [rfiData, setRfiData] = useState<any>({ inconsistencias: [], consultas_generales: [], versions: [] });
  const [showRfiModal, setShowRfiModal] = useState(false);
  const [editedInconsistencias, setEditedInconsistencias] = useState<any[]>([]);
  const [editedConsultas, setEditedConsultas] = useState<any[]>([]);
  const [savingRfi, setSavingRfi] = useState(false);

  // OT tab state
  const [otData, setOtData] = useState<any>({ metadata: {}, versions: [], is_generating: false });

  // Eco tab state
  const [ecoData, setEcoData] = useState<any>({ moneda: '', formato: '', versions: [] });
  const [costFile, setCostFile] = useState<File | null>(null);
  const [validatingCost, setValidatingCost] = useState(false);
  const [costReport, setCostReport] = useState<string | null>(null);

  // Chat modal state
  const [showChatModal, setShowChatModal] = useState(false);
  const [chatType, setChatType] = useState<'OT' | 'CONSULTAS'>('OT');
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [chatPrompt, setChatPrompt] = useState('');
  const [chatJobRunning, setChatJobRunning] = useState(false);
  const [chatJobInfo, setChatJobInfo] = useState<any>(null);
  const [sendingChat, setSendingChat] = useState(false);

  // History modal state
  const [showHistoryModal, setShowHistoryModal] = useState(false);

  const fetchTender = async () => {
    try {
      const data = await api.getTender(tenderId);
      setTender(data);
    } catch (err) {
      console.error('Error fetching tender:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTabData = async () => {
    try {
      if (activeTab === 'docs') {
        const docs = await api.getDocuments(tenderId);
        setDocuments(docs);
      } else if (activeTab === 'rfi') {
        const rfi = await api.getRfi(tenderId);
        setRfiData(rfi);
        setEditedInconsistencias(rfi.inconsistencias || []);
        setEditedConsultas(rfi.consultas_generales || []);
      } else if (activeTab === 'ot') {
        const ot = await api.getOt(tenderId);
        setOtData(ot);
      } else if (activeTab === 'eco') {
        const eco = await api.getEco(tenderId);
        setEcoData(eco);
      }
    } catch (err) {
      console.error('Error fetching tab data:', err);
    }
  };

  const fetchChat = async () => {
    try {
      const res = await api.getChat(tenderId, chatType);
      setChatMessages(res.messages || []);
      setChatJobRunning(res.is_job_running || false);
      setChatJobInfo(res.job_info || null);
    } catch (err) {
      console.error('Error fetching chat:', err);
    }
  };

  useEffect(() => {
    fetchTender();
  }, [tenderId]);

  useEffect(() => {
    fetchTabData();
  }, [tenderId, activeTab]);

  // Polling si está procesando o si hay chat job corriendo
  useEffect(() => {
    const isProcessing = tender?.status === 'PROCESANDO';
    const isJobRunning = chatJobRunning || tender?.is_chat_running;

    if (!isProcessing && !isJobRunning) return;

    const interval = setInterval(() => {
      fetchTender();
      fetchTabData();
      if (showChatModal) {
        fetchChat();
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [tender?.status, chatJobRunning, tender?.is_chat_running, showChatModal, activeTab]);

  const handleUploadDocs = async () => {
    if (!uploadFiles || uploadFiles.length === 0) return;
    setIsUploadingDocs(true);
    try {
      const formData = new FormData();
      Array.from(uploadFiles).forEach((f) => formData.append('files', f));
      await api.uploadDocuments(tenderId, formData);
      setUploadFiles(null);
      showToast('Documentos guardados correctamente.', 'success');
      await fetchTabData();
    } catch (err: any) {
      showToast(err.message || 'Error al subir documentos', 'error');
    } finally {
      setIsUploadingDocs(false);
    }
  };

  const handleReanalyze = () => {
    setShowReanalyzeConfirm(true);
  };

  const confirmReanalyze = async () => {
    setReanalyzing(true);
    setShowReanalyzeConfirm(false);
    try {
      await api.reanalyze(tenderId);
      showToast('Análisis integral ("El Show") iniciado en segundo plano.', 'success');
      await fetchTender();
    } catch (err: any) {
      showToast(err.message || 'Error al iniciar re-análisis', 'error');
    } finally {
      setReanalyzing(false);
    }
  };

  const handleSaveRfi = async () => {
    setSavingRfi(true);
    try {
      await api.updateRfi(tenderId, {
        inconsistencias: editedInconsistencias,
        consultas_generales: editedConsultas,
      });
      setShowRfiModal(false);
      await fetchTabData();
      showToast('¡Consultas guardadas y nueva versión de Word REV generada exitosamente!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Error al guardar', 'error');
    } finally {
      setSavingRfi(false);
    }
  };

  const handleSendChat = async (e: FormEvent) => {
    e.preventDefault();
    if (!chatPrompt.trim() || chatJobRunning || sendingChat) return;

    setSendingChat(true);
    const p = chatPrompt;
    setChatPrompt('');
    try {
      await api.postChatMessage(tenderId, p, chatType);
      showToast('Instrucción enviada. La nueva versión se está ensamblando.', 'info');
      await fetchChat();
    } catch (err: any) {
      showToast(err.message || 'Error al enviar mensaje', 'error');
    } finally {
      setSendingChat(false);
    }
  };

  const handleValidateCost = async () => {
    if (!costFile) return;
    setValidatingCost(true);
    setCostReport(null);
    try {
      const formData = new FormData();
      formData.append('file', costFile);
      const res = await api.validateEcoExcel(tenderId, formData);
      setCostReport(res.report || 'Validación completada sin discrepancias.');
      showToast('Validación de costos completada.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Error en validación', 'error');
    } finally {
      setValidatingCost(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400">
        <RotateCw size={32} className="animate-spin mx-auto text-blue-600 mb-3" />
        <span className="font-semibold text-sm">Cargando detalles de la licitación...</span>
      </div>
    );
  }

  if (!tender) {
    return (
      <div className="py-12 text-center text-slate-500">
        <p>No se encontró la licitación seleccionada.</p>
        <button onClick={onBack} className="mt-4 text-blue-600 font-semibold hover:underline">
          Volver al Dashboard
        </button>
      </div>
    );
  }

  const isProcessing = tender.status === 'PROCESANDO';

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={onBack}
            className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer"
          >
            <ArrowLeft size={18} />
          </button>
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center text-2xl font-bold shadow-md shadow-blue-600/20">
              📁
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-900 tracking-tight leading-none">
                {tender.name}
              </h1>
              <div className="text-xs text-slate-500 mt-1.5 flex items-center space-x-2">
                <span>Creada: {formatArgentinaDate(tender.created_at)}</span>
              </div>
            </div>
          </div>
        </div>

        <div>
          {tender.status === 'COMPLETADO' ? (
            <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              <CheckCircle2 size={14} className="mr-1.5 text-emerald-600" />
              Completado
            </span>
          ) : isProcessing ? (
            <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200 animate-pulse">
              <RotateCw size={14} className="mr-1.5 text-blue-600 animate-spin" />
              Procesando en Segundo Plano
            </span>
          ) : (
            <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
              {tender.status}
            </span>
          )}
        </div>
      </div>

      {/* PROCESSING STATE BANNER */}
      {isProcessing && (
        <div className="bg-blue-50 border-2 border-blue-200 rounded-2xl p-6 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <RotateCw size={24} className="text-blue-600 animate-spin" />
              <div>
                <div className="font-bold text-slate-900 text-base">
                  {tender.progress_msg || 'Procesando documentos y extrayendo pliego...'}
                </div>
                <div className="text-xs text-slate-500">
                  Esta pantalla se actualiza en tiempo real sin recargar el navegador.
                </div>
              </div>
            </div>
            <div className="text-xl font-black text-blue-600">
              {tender.progress || 10}%
            </div>
          </div>
          <div className="w-full h-3 bg-blue-200/50 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 rounded-full transition-all duration-500"
              style={{ width: `${tender.progress || 10}%` }}
            />
          </div>
        </div>
      )}

      {/* AI ASSISTANT RUNNING BANNER */}
      {tender.is_chat_running && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-1.5 border-blue-200 rounded-xl p-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">🤖</span>
            <div>
              <div className="font-bold text-blue-900 text-sm">
                Asistente IA generando nueva versión en segundo plano...
              </div>
              <div className="text-xs text-blue-700">
                El documento se está ensamblando con las instrucciones recibidas. La vista se actualizará apenas termine.
              </div>
            </div>
          </div>
          <span className="bg-blue-200 text-blue-800 text-[10px] font-extrabold uppercase px-3 py-1 rounded-full">
            EN PROCESO
          </span>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-8">
          {[
            { id: 'docs', label: '📁 Documentos' },
            { id: 'rfi', label: '❓ Consultas (RFI)' },
            { id: 'ot', label: '📄 Oferta Técnica' },
            { id: 'eco', label: '📊 Oferta Económica' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-1 border-b-2 font-bold text-sm transition-colors cursor-pointer ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* TAB CONTENT */}

      {/* 1. DOCUMENTOS TAB */}
      {activeTab === 'docs' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Left Column: Actions */}
          <div ref={leftDocsColRef} className="space-y-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
              <h3 className="font-bold text-slate-800 text-sm">Subir Nuevos Pliegos o Anexos</h3>
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.xlsx,.xls"
                onChange={(e) => setUploadFiles(e.target.files)}
                className="block w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              <button
                onClick={handleUploadDocs}
                disabled={!uploadFiles || isUploadingDocs}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs py-2.5 px-4 rounded-xl flex items-center justify-center space-x-1.5 transition-colors disabled:opacity-40 cursor-pointer shadow-md shadow-blue-600/20"
              >
                {isUploadingDocs ? <RotateCw size={14} className="animate-spin" /> : <UploadCloud size={14} />}
                <span>Guardar Archivos</span>
              </button>
            </div>

            <div className="bg-gradient-to-br from-blue-900 to-slate-900 text-white rounded-2xl p-5 shadow-lg space-y-3">
              <div className="flex items-center space-x-2 text-lime-400 font-bold text-sm">
                <Sparkles size={16} />
                <span>Análisis Inteligente Completo</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Ejecuta el procesamiento IA integral ("El Show") para re-extraer todos los requerimientos, especificaciones y generar nuevas revisiones.
              </p>
              <button
                onClick={handleReanalyze}
                disabled={reanalyzing || isProcessing}
                className="w-full bg-lime-400 hover:bg-lime-300 text-slate-950 font-bold text-xs py-2.5 px-4 rounded-xl flex items-center justify-center space-x-1.5 transition-all shadow-md cursor-pointer disabled:opacity-40"
              >
                {reanalyzing ? <RotateCw size={14} className="animate-spin" /> : <span>🚀 Iniciar Análisis (El Show)</span>}
              </button>
            </div>

            {/* SharePoint status card */}
            <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm flex items-center space-x-3 text-xs text-slate-600">
              <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                ☁️
              </div>
              <div>
                <div className="font-bold text-slate-800">Microsoft 365 & SharePoint</div>
                <div className="text-[11px] text-slate-400">Sincronización automática de carpetas activa</div>
              </div>
            </div>

            <button
              onClick={() => setShowHistoryModal(true)}
              className="w-full bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-semibold text-xs py-2.5 px-4 rounded-xl flex items-center justify-center space-x-2 transition-colors cursor-pointer"
            >
              <History size={14} />
              <span>Ver Historial de Interacciones IA</span>
            </button>
          </div>

          {/* Right Column: Uploaded Documents Table matching left column height with internal scroll */}
          <div
            style={leftDocsHeight ? { height: `${leftDocsHeight}px` } : undefined}
            className="md:col-span-2 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex flex-col overflow-hidden min-h-[440px]"
          >
            <div className="flex justify-between items-center pb-3 border-b border-slate-100 shrink-0">
              <div className="flex items-center space-x-2">
                <h3 className="font-bold text-slate-800 text-sm">Documentos Cargados</h3>
                <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-bold text-xs">
                  {documents.length}
                </span>
              </div>
              <span className="text-xs text-slate-400">Archivos almacenados en servidor</span>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto overflow-x-auto mt-1">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-white z-10">
                  <tr className="border-b border-slate-200 text-slate-400 font-bold uppercase text-[11px]">
                    <th className="py-2.5 px-3 bg-white">Archivo</th>
                    <th className="py-2.5 px-3 bg-white">Tamaño</th>
                    <th className="py-2.5 px-3 bg-white">Modificado</th>
                    <th className="py-2.5 px-3 text-right bg-white">Descarga</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {documents.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-12 text-center text-slate-400">
                        No hay archivos en la carpeta de esta licitación.
                      </td>
                    </tr>
                  ) : (
                    documents.map((doc, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/75 transition-colors">
                        <td className="py-3 px-3 font-medium text-slate-800 flex items-center space-x-2">
                          <FileText size={16} className="text-blue-500 shrink-0" />
                          <span className="truncate max-w-xs">{doc.name}</span>
                        </td>
                        <td className="py-3 px-3 text-slate-500 whitespace-nowrap">{doc.size_kb} KB</td>
                        <td className="py-3 px-3 text-slate-500 whitespace-nowrap">{doc.modified}</td>
                        <td className="py-3 px-3 text-right whitespace-nowrap">
                          <a
                            href={doc.download_url}
                            download
                            className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 font-semibold cursor-pointer"
                          >
                            <Download size={14} />
                            <span>Bajar</span>
                          </a>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 2. CONSULTAS (RFI) TAB */}
      {activeTab === 'rfi' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
              <h3 className="font-bold text-slate-800 text-sm">Resumen de Consultas al Pliego</h3>
              <div className="border border-slate-100 rounded-2xl p-3 bg-slate-50/75 space-y-1">
                <AdaptiveInfoRow
                  icon="⚠️"
                  label="Inconsistencias Detectadas"
                  value={rfiData.inconsistencias?.length ? `${rfiData.inconsistencias.length} detectadas` : '0 detectadas'}
                  badge={
                    <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold text-[10px]">
                      {rfiData.inconsistencias?.length || 0}
                    </span>
                  }
                />
                <AdaptiveInfoRow
                  icon="❓"
                  label="Consultas Generales"
                  value={rfiData.consultas_generales?.length ? `${rfiData.consultas_generales.length} generadas` : '0 generadas'}
                  badge={
                    <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-bold text-[10px]">
                      {rfiData.consultas_generales?.length || 0}
                    </span>
                  }
                />
              </div>

              <button
                onClick={() => setShowRfiModal(true)}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-2.5 px-4 rounded-xl flex items-center justify-center space-x-2 shadow-md shadow-blue-600/20 transition-colors cursor-pointer"
              >
                <HelpCircle size={15} />
                <span>Gestor de Consultas e Incongruencias ✏️</span>
              </button>

              <button
                onClick={() => {
                  setChatType('CONSULTAS');
                  setShowChatModal(true);
                  fetchChat();
                }}
                className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs py-2.5 px-4 rounded-xl flex items-center justify-center space-x-2 transition-colors cursor-pointer"
              >
                <Sparkles size={15} className="text-lime-400" />
                <span>✨ Asistente IA (Ajustar Consultas)</span>
              </button>
            </div>
          </div>

          <div className="md:col-span-2 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="font-bold text-slate-800 text-sm">Versiones del Documento Word de Consultas</h3>
            {rfiData.versions?.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-xs">
                Aún no se han generado versiones de consultas. Pulsa en "Gestor de Consultas" para generar una.
              </div>
            ) : (
              <div className="space-y-2">
                {rfiData.versions.map((v: any, i: number) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs"
                  >
                    <div className="flex items-center space-x-3 min-w-0 flex-1 mr-4">
                      <span className="font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-[10px] shrink-0">
                        {v.revision}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-slate-800 break-words">{v.name}</div>
                        <div className="text-[11px] text-slate-400">{v.date}</div>
                      </div>
                    </div>
                    <a
                      href={v.download_url}
                      download
                      className="bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold px-3 py-1.5 rounded-lg flex items-center space-x-1 transition-colors shrink-0"
                    >
                      <Download size={14} />
                      <span>Descargar Word</span>
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. OFERTA TÉCNICA (OT) TAB */}
      {activeTab === 'ot' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
              <h3 className="font-bold text-slate-800 text-sm">Información de la Oferta Técnica</h3>
              <div className="border border-slate-100 rounded-2xl p-3 bg-slate-50/75 space-y-1">
                <AdaptiveInfoRow icon="🏢" label="Cliente" value={otData.metadata?.cliente} />
                <AdaptiveInfoRow icon="🏭" label="Planta" value={otData.metadata?.planta} />
                <AdaptiveInfoRow icon="📄" label="Licitación" value={otData.metadata?.proceso} />
                <AdaptiveInfoRow icon="👤" label="Responsable" value="Sebastien Martinet" />
              </div>

              <button
                onClick={() => {
                  setChatType('OT');
                  setShowChatModal(true);
                  fetchChat();
                }}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-3 px-4 rounded-xl flex items-center justify-center space-x-2 shadow-md shadow-blue-600/20 transition-all cursor-pointer"
              >
                <Sparkles size={16} className="text-lime-400" />
                <span>✨ Asistente IA (Modificar OT)</span>
              </button>
            </div>
          </div>

          <div className="md:col-span-2 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="font-bold text-slate-800 text-sm">Versiones Ensambladas de la Oferta Técnica</h3>
            {otData.versions?.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-xs">
                No hay versiones generadas aún. Inicia "El Show" desde la pestaña Documentos para generar la REV00.
              </div>
            ) : (
              <div className="space-y-2">
                {otData.versions.map((v: any, i: number) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs"
                  >
                    <div className="flex items-center space-x-3 min-w-0 flex-1 mr-4">
                      <span className="font-bold px-2 py-0.5 rounded bg-blue-600 text-white text-[10px] shrink-0">
                        {v.revision}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-slate-800 break-words">{v.name}</div>
                        <div className="text-[11px] text-slate-400">{v.date}</div>
                      </div>
                    </div>
                    <a
                      href={v.download_url}
                      download
                      className="bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold px-3 py-1.5 rounded-lg flex items-center space-x-1 transition-colors shrink-0"
                    >
                      <Download size={14} />
                      <span>Descargar Word</span>
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. OFERTA ECONÓMICA TAB */}
      {activeTab === 'eco' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
              <h3 className="font-bold text-slate-800 text-sm">Base para Costeo Económico</h3>
              <div className="border border-slate-100 rounded-2xl p-3 bg-slate-50/75 space-y-1">
                <AdaptiveInfoRow icon="💰" label="Moneda" value={ecoData.moneda} fallback="No especificada" />
                <AdaptiveInfoRow icon="📊" label="Formato" value="Excel Estándar IMA" />
              </div>

              <div className="border-t border-slate-100 pt-4 space-y-3">
                <h4 className="font-bold text-slate-800 text-xs">🔍 Verificación de Costos con IA</h4>
                <p className="text-[11px] text-slate-500 leading-tight">
                  Sube el Excel cotizado para que Claude detecte posibles errores frente al pliego.
                </p>
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={(e) => setCostFile(e.target.files?.[0] || null)}
                  className="block w-full text-xs text-slate-500 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 truncate cursor-pointer"
                />
                <button
                  onClick={handleValidateCost}
                  disabled={!costFile || validatingCost}
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-2.5 px-4 rounded-xl flex items-center justify-center space-x-1.5 shadow-md shadow-blue-600/20 disabled:opacity-40 transition-colors cursor-pointer"
                >
                  {validatingCost ? <RotateCw size={14} className="animate-spin" /> : <span>Analizar con IA 🤖</span>}
                </button>
              </div>
            </div>
          </div>

          <div className="md:col-span-2 space-y-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
              <h3 className="font-bold text-slate-800 text-sm">Archivos Excel de Costos Generados</h3>
              {ecoData.versions?.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-xs">
                  No se han generado planillas Excel de costos todavía.
                </div>
              ) : (
                <div className="space-y-2">
                  {ecoData.versions.map((v: any, i: number) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs"
                    >
                      <div className="flex items-center space-x-3 min-w-0 flex-1 mr-4">
                        <FileCheck size={18} className="text-emerald-600 shrink-0" />
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold text-slate-800 break-words">{v.name}</div>
                          <div className="text-[11px] text-slate-400">{v.date}</div>
                        </div>
                      </div>
                      <a
                        href={v.download_url}
                        download
                        className="bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-semibold px-3 py-1.5 rounded-lg flex items-center space-x-1 transition-colors shrink-0"
                      >
                        <Download size={14} />
                        <span>Descargar Excel</span>
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {costReport && (
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-2 animate-in fade-in">
                <div className="flex items-center space-x-2 text-sm font-bold text-slate-800">
                  <Sparkles size={16} className="text-blue-600" />
                  <span>Informe de Discrepancias Detectadas por IA</span>
                </div>
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">
                  {costReport}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* RFI EDIT MODAL */}
      {showRfiModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[85vh] flex flex-col animate-in fade-in zoom-in-95">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-bold text-base text-slate-900">
                  Gestor de Consultas e Incongruencias
                </h3>
                <p className="text-xs text-slate-500">
                  Revisa y edita el detalle de consultas detectadas para generar una nueva versión en Word.
                </p>
              </div>
              <button onClick={() => setShowRfiModal(false)} className="text-slate-400 hover:text-slate-600 p-1">
                <X size={20} />
              </button>
            </div>

            <div className="overflow-y-auto space-y-6 flex-1 pr-2">
              {/* Inconsistencias */}
              <div>
                <h4 className="text-xs font-bold uppercase text-amber-600 tracking-wider mb-2">
                  ⚠️ Inconsistencias (Alertas)
                </h4>
                {editedInconsistencias.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No se registraron inconsistencias.</p>
                ) : (
                  <div className="space-y-3">
                    {editedInconsistencias.map((inc, i) => (
                      <div key={i} className="p-3 bg-amber-50/50 border border-amber-200 rounded-xl space-y-2 text-xs">
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-[10px] font-bold text-slate-500">Tipo de Alerta</label>
                            <input
                              type="text"
                              value={inc.tipo || ''}
                              onChange={(e) => {
                                const copy = [...editedInconsistencias];
                                copy[i].tipo = e.target.value;
                                setEditedInconsistencias(copy);
                              }}
                              className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] font-bold text-slate-500">Documentos Relacionados</label>
                            <input
                              type="text"
                              value={Array.isArray(inc.documentos_conflicto) ? inc.documentos_conflicto.join(', ') : inc.documentos_conflicto || ''}
                              onChange={(e) => {
                                const copy = [...editedInconsistencias];
                                copy[i].documentos_conflicto = e.target.value.split(',').map((s) => s.trim());
                                setEditedInconsistencias(copy);
                              }}
                              className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-slate-500">Descripción</label>
                          <textarea
                            rows={2}
                            value={inc.descripcion || ''}
                            onChange={(e) => {
                              const copy = [...editedInconsistencias];
                              copy[i].descripcion = e.target.value;
                              setEditedInconsistencias(copy);
                            }}
                            className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Consultas Generales */}
              <div>
                <h4 className="text-xs font-bold uppercase text-blue-600 tracking-wider mb-2">
                  ❓ Consultas Generales
                </h4>
                {editedConsultas.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No se registraron consultas generales.</p>
                ) : (
                  <div className="space-y-3">
                    {editedConsultas.map((c, i) => (
                      <div key={i} className="p-3 bg-blue-50/50 border border-blue-200 rounded-xl space-y-2 text-xs">
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-[10px] font-bold text-slate-500">Categoría</label>
                            <input
                              type="text"
                              value={c.categoria || ''}
                              onChange={(e) => {
                                const copy = [...editedConsultas];
                                copy[i].categoria = e.target.value;
                                setEditedConsultas(copy);
                              }}
                              className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] font-bold text-slate-500">Archivo Origen</label>
                            <input
                              type="text"
                              value={c.archivo_origen || ''}
                              onChange={(e) => {
                                const copy = [...editedConsultas];
                                copy[i].archivo_origen = e.target.value;
                                setEditedConsultas(copy);
                              }}
                              className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-slate-500">Consulta</label>
                          <textarea
                            rows={2}
                            value={c.consulta || ''}
                            onChange={(e) => {
                              const copy = [...editedConsultas];
                              copy[i].consulta = e.target.value;
                              setEditedConsultas(copy);
                            }}
                            className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end space-x-2 border-t border-slate-100 pt-3">
              <button
                onClick={() => setShowRfiModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveRfi}
                disabled={savingRfi}
                className="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-2 px-5 rounded-xl flex items-center space-x-1.5 shadow-md shadow-blue-600/30 cursor-pointer disabled:opacity-50"
              >
                {savingRfi ? <RotateCw size={14} className="animate-spin" /> : <Save size={14} />}
                <span>Guardar Cambios y Generar Word</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI ASSISTANT CHAT MODAL */}
      {showChatModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 flex flex-col h-[75vh] animate-in fade-in zoom-in-95">
            {/* Header */}
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-xl">✨</span>
                <div>
                  <h3 className="font-bold text-sm text-slate-900">
                    Asistente IA — {chatType === 'OT' ? 'Oferta Técnica' : 'Consultas al Pliego'}
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Sugiere cambios al documento (ej: "Agrega un supervisor electromecánico", "Ajusta el plazo a 30 días")
                  </p>
                </div>
              </div>
              <button onClick={() => setShowChatModal(false)} className="text-slate-400 hover:text-slate-600 p-1">
                <X size={20} />
              </button>
            </div>

            {/* Active Job Alert */}
            {chatJobRunning && (
              <div className="my-2 p-3 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between text-xs text-blue-900">
                <div className="flex items-center space-x-2">
                  <RotateCw size={14} className="animate-spin text-blue-600" />
                  <span className="font-semibold">
                    Generando nueva versión con IA en segundo plano
                    {chatJobInfo?.prompt ? `: "${chatJobInfo.prompt.slice(0, 50)}..."` : '...'}
                  </span>
                </div>
                <span className="bg-blue-200 text-blue-800 text-[10px] font-bold px-2 py-0.5 rounded">
                  EN PROCESO
                </span>
              </div>
            )}

            {/* Messages container */}
            <div className="flex-1 overflow-y-auto space-y-3 py-3 pr-2">
              {chatMessages.map((msg, i) => {
                const isUser = msg.role === 'user';
                return (
                  <div key={i} className={`flex items-start space-x-2.5 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 font-bold ${
                        isUser ? 'bg-slate-700 text-white' : 'bg-blue-600 text-white'
                      }`}
                    >
                      {isUser ? '👤' : '🤖'}
                    </div>
                    <div
                      className={`p-3 rounded-2xl text-xs max-w-[80%] whitespace-pre-wrap leading-relaxed ${
                        isUser
                          ? 'bg-slate-800 text-white rounded-tr-none'
                          : 'bg-blue-50/80 border border-blue-100 text-slate-800 rounded-tl-none'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Input form */}
            <form onSubmit={handleSendChat} className="border-t border-slate-100 pt-3 flex space-x-2">
              <input
                type="text"
                disabled={chatJobRunning || sendingChat}
                value={chatPrompt}
                onChange={(e) => setChatPrompt(e.target.value)}
                placeholder={
                  chatJobRunning
                    ? 'Esperá a que finalice la generación en curso...'
                    : 'Escribe tu instrucción para la IA...'
                }
                className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={chatJobRunning || sendingChat || !chatPrompt.trim()}
                className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-4 py-2.5 rounded-xl flex items-center justify-center transition-all shadow-md shadow-blue-600/30 disabled:opacity-40 cursor-pointer"
              >
                <Send size={15} />
              </button>
            </form>
          </div>
        </div>
      )}

      {/* IA INTERACTION HISTORY MODAL */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[80vh] flex flex-col animate-in fade-in zoom-in-95">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
                <History size={16} className="text-blue-600" />
                <span>Historial de Interacciones con la IA</span>
              </h3>
              <button onClick={() => setShowHistoryModal(false)} className="text-slate-400 hover:text-slate-600 p-1">
                <X size={20} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-3 py-2 pr-2 text-xs">
              {chatMessages.length === 0 ? (
                <p className="text-slate-400 text-center py-6">No has interactuado con la IA todavía en este proyecto.</p>
              ) : (
                chatMessages.map((m, i) => (
                  <div key={i} className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                    <div className="font-bold text-slate-500 text-[10px] uppercase">
                      {m.role === 'user' ? '👤 Tú' : '🤖 Asistente IA'}
                    </div>
                    <div className="text-slate-800 leading-relaxed whitespace-pre-wrap">{m.content}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* CONFIRM MODAL FOR RE-ANALYSIS ("EL SHOW") */}
      <ConfirmModal
        isOpen={showReanalyzeConfirm}
        title="Iniciar Análisis Integral ('El Show')"
        message="¿Deseas iniciar el procesamiento inteligente completo con todos los documentos y anexos subidos? Esta tarea se ejecutará en segundo plano con Claude y ensamblará las nuevas revisiones de Word."
        confirmText="🚀 Iniciar El Show"
        cancelText="Cancelar"
        type="info"
        loading={reanalyzing}
        onConfirm={confirmReanalyze}
        onCancel={() => setShowReanalyzeConfirm(false)}
      />
    </div>
  );
};
