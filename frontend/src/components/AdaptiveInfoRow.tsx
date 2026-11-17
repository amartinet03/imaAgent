import type { FC, ReactNode } from 'react';

export interface AdaptiveInfoRowProps {
  icon?: ReactNode;
  label: string;
  value?: string | number | null;
  fallback?: string;
  className?: string;
  badge?: ReactNode;
  forceVertical?: boolean;
}

/**
 * AdaptiveInfoRow renders key-value metadata cleanly.
 * If the value is long (> 32 chars or multi-line), it automatically adapts
 * to a full-width vertical layout with an enclosed readable text card so
 * it NEVER collides with or crushes the label, and preserves long paragraphs.
 * If the value is short, it renders a sleek horizontal row with guaranteed spacing.
 */
export const AdaptiveInfoRow: FC<AdaptiveInfoRowProps> = ({
  icon,
  label,
  value,
  fallback = 'No especificado',
  className = '',
  badge,
  forceVertical = false,
}) => {
  const textValue = value !== undefined && value !== null ? String(value).trim() : '';
  const displayValue = textValue || fallback;

  // In sidebar cards (~260px usable width), values over 32 chars or with linebreaks
  // cannot fit horizontally next to a label without squishing.
  const isLong = forceVertical || displayValue.length > 32 || displayValue.includes('\n');

  if (isLong) {
    return (
      <div className={`py-2 border-b border-slate-200/60 last:border-b-0 space-y-1.5 ${className}`}>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500 font-semibold flex items-center space-x-1.5 shrink-0">
            {icon && <span className="text-sm shrink-0 leading-none">{icon}</span>}
            <span>{label}:</span>
          </span>
          {badge}
        </div>
        <div className="text-xs font-medium text-slate-800 leading-relaxed break-words whitespace-pre-wrap bg-white/90 p-2.5 rounded-xl border border-slate-200/80 shadow-2xs">
          {displayValue}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`py-2 border-b border-slate-200/60 last:border-b-0 flex items-start justify-between gap-3 text-xs ${className}`}
    >
      <span className="text-slate-500 font-semibold shrink-0 flex items-center space-x-1.5 pt-0.5">
        {icon && <span className="text-sm shrink-0 leading-none">{icon}</span>}
        <span>{label}:</span>
      </span>
      <div className="text-right min-w-0 flex items-center justify-end space-x-2">
        <span className="font-semibold text-slate-800 break-words text-right">
          {displayValue}
        </span>
        {badge}
      </div>
    </div>
  );
};
