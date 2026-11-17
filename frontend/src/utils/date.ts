/**
 * Formatea una fecha/timestamp a la zona horaria de Argentina (America/Argentina/Buenos_Aires - UTC-3)
 * en el formato requerido: dd/mm/aaaa hh:mm:ss
 */
export function formatArgentinaDate(dateStr?: string | null): string {
  if (!dateStr) return 'Reciente';

  try {
    let normalized = String(dateStr).trim();

    // Normalizar formato 'YYYY-MM-DD HH:mm:ss' a ISO 'YYYY-MM-DDTHH:mm:ss'
    if (!normalized.includes('T')) {
      normalized = normalized.replace(' ', 'T');
    }

    // Si viene sin indicador de zona horaria (típico de SQLite o CURRENT_TIMESTAMP en UTC), asumir UTC
    if (!normalized.endsWith('Z') && !normalized.includes('+') && !/-\d\d:\d\d$/.test(normalized)) {
      normalized += 'Z';
    }

    const d = new Date(normalized);
    if (isNaN(d.getTime())) return dateStr;

    const formatter = new Intl.DateTimeFormat('es-AR', {
      timeZone: 'America/Argentina/Buenos_Aires',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });

    const parts = formatter.formatToParts(d);
    const day = parts.find((p) => p.type === 'day')?.value || '';
    const month = parts.find((p) => p.type === 'month')?.value || '';
    const year = parts.find((p) => p.type === 'year')?.value || '';
    const hour = parts.find((p) => p.type === 'hour')?.value || '';
    const minute = parts.find((p) => p.type === 'minute')?.value || '';
    const second = parts.find((p) => p.type === 'second')?.value || '';

    return `${day}/${month}/${year} ${hour}:${minute}:${second}`;
  } catch {
    return String(dateStr);
  }
}
