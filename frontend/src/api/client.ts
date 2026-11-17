const API_BASE = '/api';

export function getAuthToken(): string | null {
  return localStorage.getItem('ima_token');
}

export function setAuthToken(token: string, username: string) {
  localStorage.setItem('ima_token', token);
  localStorage.setItem('ima_user', username);
}

export function clearAuthToken() {
  localStorage.removeItem('ima_token');
  localStorage.removeItem('ima_user');
}

export function getCurrentUser(): string {
  return localStorage.getItem('ima_user') || 'Usuario';
}

export function isAuthenticated(): boolean {
  return !!getAuthToken();
}

async function request(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = `Error ${response.status}: ${response.statusText}`;
    try {
      const data = await response.json();
      if (data.detail) errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  // Auth
  login: (credentials: { username: string; password: string }) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  changePassword: (data: { username: string; current_password: string; new_password: string }) =>
    request('/auth/change-password', { method: 'POST', body: JSON.stringify(data) }),

  // Tenders
  getStats: () => request('/tenders/stats'),
  getTenders: () => request('/tenders'),
  getTender: (id: number) => request(`/tenders/${id}`),
  deleteTender: (id: number) => request(`/tenders/${id}`, { method: 'DELETE' }),
  createTender: (formData: FormData) =>
    request('/tenders', { method: 'POST', body: formData }),

  // Documents
  getDocuments: (id: number) => request(`/tenders/${id}/documents`),
  uploadDocuments: (id: number, formData: FormData) =>
    request(`/tenders/${id}/documents/upload`, { method: 'POST', body: formData }),
  reanalyze: (id: number) =>
    request(`/tenders/${id}/reanalyze`, { method: 'POST' }),

  // RFI
  getRfi: (id: number) => request(`/tenders/${id}/rfi`),
  updateRfi: (id: number, data: { inconsistencias: any[]; consultas_generales: any[] }) =>
    request(`/tenders/${id}/rfi`, { method: 'PUT', body: JSON.stringify(data) }),

  // OT
  getOt: (id: number) => request(`/tenders/${id}/ot`),

  // Chat
  getChat: (id: number, chatType = 'OT') => request(`/tenders/${id}/chat?chat_type=${chatType}`),
  postChatMessage: (id: number, prompt: string, chatType = 'OT') =>
    request(`/tenders/${id}/chat`, { method: 'POST', body: JSON.stringify({ prompt, chat_type: chatType }) }),

  // Eco
  getEco: (id: number) => request(`/tenders/${id}/eco`),
  generateEcoExcel: (id: number) => request(`/tenders/${id}/eco/generate`, { method: 'POST' }),
  validateEcoExcel: (id: number, formData: FormData) =>
    request(`/tenders/${id}/eco/validate`, { method: 'POST', body: formData }),

  // Radar
  getOpportunities: () => request('/radar/opportunities'),
  getPendingOpportunities: () => request('/radar/opportunities/pending'),
  approveOpportunity: (id: number) => request(`/radar/opportunities/${id}/approve`, { method: 'POST' }),
  rejectOpportunity: (id: number) => request(`/radar/opportunities/${id}/reject`, { method: 'POST' }),
  deleteOpportunity: (id: number) => request(`/radar/opportunities/${id}`, { method: 'DELETE' }),
  triggerScan: () => request('/radar/scan', { method: 'POST' }),

  // Radar Portals & Keywords
  getPortals: () => request('/radar/portals'),
  createPortal: (portal: { name: string; url: string; frequency?: string }) =>
    request('/radar/portals', { method: 'POST', body: JSON.stringify(portal) }),
  togglePortal: (id: number) => request(`/radar/portals/${id}/toggle`, { method: 'PUT' }),
  deletePortal: (id: number) => request(`/radar/portals/${id}`, { method: 'DELETE' }),

  getKeywords: () => request('/radar/keywords'),
  createKeyword: (keyword: string) =>
    request('/radar/keywords', { method: 'POST', body: JSON.stringify({ keyword }) }),
  deleteKeyword: (id: number) => request(`/radar/keywords/${id}`, { method: 'DELETE' }),

  getDaemon: () => request('/radar/daemon'),
  updateDaemon: (settings: any) => request('/radar/daemon', { method: 'POST', body: JSON.stringify(settings) }),

  getWeeklyDigestStatus: () => request('/radar/weekly-digest-status'),
  sendWeeklyDigest: () => request('/radar/send-weekly-digest', { method: 'POST' }),
};
