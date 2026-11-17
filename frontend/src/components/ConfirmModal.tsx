import { useEffect, type FC } from 'react';
import { AlertTriangle, Trash2, Sparkles, HelpCircle, X, RotateCw } from 'lucide-react';

export type ConfirmModalType = 'danger' | 'warning' | 'info' | 'success';

export interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: ConfirmModalType;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmModal: FC<ConfirmModalProps> = ({
  isOpen,
  title,
  message,
  confirmText = 'Confirmar',
  cancelText = 'Cancelar',
  type = 'danger',
  loading = false,
  onConfirm,
  onCancel,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !loading) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, loading, onCancel]);

  if (!isOpen) return null;

  const renderIcon = () => {
    switch (type) {
      case 'danger':
        return (
          <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center shrink-0 border border-rose-100 shadow-inner">
            <Trash2 size={24} />
          </div>
        );
      case 'warning':
        return (
          <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0 border border-amber-100 shadow-inner">
            <AlertTriangle size={24} />
          </div>
        );
      case 'info':
        return (
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100 shadow-inner">
            <Sparkles size={24} />
          </div>
        );
      case 'success':
        return (
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100 shadow-inner">
            <HelpCircle size={24} />
          </div>
        );
    }
  };

  const getConfirmButtonClasses = () => {
    switch (type) {
      case 'danger':
        return 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/30';
      case 'warning':
        return 'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-600/30';
      case 'info':
        return 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/30';
      case 'success':
        return 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30';
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150"
      onClick={() => {
        if (!loading) onCancel();
      }}
    >
      <div
        className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-200/90 space-y-5 animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3.5">
            {renderIcon()}
            <div>
              <h3 className="font-extrabold text-slate-900 text-base leading-snug">
                {title}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Acción definitiva del sistema</p>
            </div>
          </div>
          {!loading && (
            <button
              onClick={onCancel}
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>
          )}
        </div>

        <div className="text-sm text-slate-600 leading-relaxed bg-slate-50/80 p-4 rounded-2xl border border-slate-100">
          {message}
        </div>

        <div className="flex items-center justify-end space-x-2.5 pt-1">
          <button
            type="button"
            disabled={loading}
            onClick={onCancel}
            className="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 hover:text-slate-800 transition-colors disabled:opacity-50 cursor-pointer"
          >
            {cancelText}
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={onConfirm}
            className={`px-5 py-2.5 rounded-xl text-xs font-bold shadow-lg transition-all flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${getConfirmButtonClasses()}`}
          >
            {loading && <RotateCw size={14} className="animate-spin" />}
            <span>{confirmText}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
