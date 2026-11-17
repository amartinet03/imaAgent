import { useState, useRef, type FC, type FormEvent } from 'react';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { UploadCloud, FileText, X, ArrowLeft, RotateCw, CheckCircle2 } from 'lucide-react';

interface NewTenderProps {
  onBack: () => void;
  onCreated: (tenderId: number) => void;
}

export const NewTender: FC<NewTenderProps> = ({ onBack, onCreated }) => {
  const { showToast } = useToast();
  const [name, setName] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFilesAdded = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const validExtensions = ['.pdf', '.docx', '.xlsx', '.xls'];
    const validFiles: File[] = [];

    Array.from(newFiles).forEach((f) => {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase();
      if (validExtensions.includes(ext)) {
        validFiles.push(f);
      }
    });

    setFiles((prev) => [...prev, ...validFiles]);
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Por favor ingresa un nombre para el proyecto o licitación.');
      return;
    }
    if (files.length === 0) {
      setError('Debes subir al menos un pliego o anexo.');
      return;
    }

    setError(null);
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('name', name);
      files.forEach((file) => {
        formData.append('files', file);
      });

      const res = await api.createTender(formData);
      showToast('¡Licitación creada! Procesando documentos en segundo plano.', 'success');
      if (res.tender_id) {
        onCreated(res.tender_id);
      } else {
        onBack();
      }
    } catch (err: any) {
      setError(err.message || 'Error al procesar la licitación');
      setUploading(false);
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onBack}
          className="p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer shadow-sm"
          title="Volver al Dashboard"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <span>Nueva Licitación</span>
            <span className="text-xl">📁</span>
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Sube los pliegos y anexos. El sistema los procesará en segundo plano con IA.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-2xl text-sm flex items-center justify-between shadow-sm">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-700 cursor-pointer">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Main Single Card Form occupying full available width */}
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6 w-full">
        {/* Campo: Nombre de la Licitación */}
        <div className="space-y-2">
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
            Nombre de la Licitación / Proyecto *
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej: Licitación YPF Mantenimiento Plantas La Plata"
            className="w-full px-4 py-3.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
          />
        </div>

        {/* Campo: Zona de Arrastre de Pliegos */}
        <div className="space-y-2">
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
            Pliegos, Anexos y Documentación Técnica *
          </label>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              handleFilesAdded(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[240px] w-full ${
              isDragOver
                ? 'border-blue-500 bg-blue-50/60 scale-[1.005]'
                : 'border-slate-300 hover:border-blue-400 bg-slate-50/50 hover:bg-slate-50/80'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.xlsx,.xls"
              className="hidden"
              onChange={(e) => handleFilesAdded(e.target.files)}
            />
            <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4 shadow-sm">
              <UploadCloud size={32} />
            </div>
            <div className="font-bold text-slate-800 text-base">
              Arrastra los pliegos aquí o haz clic para seleccionar
            </div>
            <div className="text-xs text-slate-400 mt-1.5">
              Soporta PDF, Word (.docx) y planillas Excel (.xlsx, .xls)
            </div>
          </div>
        </div>

        {/* Lista de archivos seleccionados */}
        {files.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                Archivos Seleccionados ({files.length})
              </span>
              <button
                type="button"
                onClick={() => setFiles([])}
                className="text-xs text-rose-500 hover:text-rose-700 font-semibold cursor-pointer"
              >
                Quitar todos
              </button>
            </div>
            <div className="space-y-2">
              {files.map((file, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-700 transition-colors hover:bg-slate-100/60"
                >
                  <div className="flex items-center space-x-3 truncate">
                    <FileText size={18} className="text-blue-500 shrink-0" />
                    <span className="font-semibold text-slate-800 truncate">{file.name}</span>
                    <span className="text-xs text-slate-400 shrink-0">
                      ({Math.round(file.size / 1024)} KB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(i)}
                    className="text-slate-400 hover:text-rose-500 p-1.5 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
                    title="Quitar archivo"
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Botón de acción */}
        <div className="pt-2 space-y-3">
          <button
            type="submit"
            disabled={uploading || files.length === 0 || !name.trim()}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-4 px-6 rounded-xl flex items-center justify-center space-x-2 shadow-lg shadow-blue-600/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer text-base"
          >
            {uploading ? (
              <>
                <RotateCw size={18} className="animate-spin" />
                <span>Procesando e iniciando análisis en segundo plano...</span>
              </>
            ) : (
              <>
                <CheckCircle2 size={18} />
                <span>Procesar Archivos en Segundo Plano 🚀</span>
              </>
            )}
          </button>
          <p className="text-xs text-center text-slate-400 leading-relaxed">
            El análisis de pliegos y la extracción con Claude Sonnet continuará en segundo plano. Podrás seguir navegando.
          </p>
        </div>
      </form>
    </div>
  );
};
