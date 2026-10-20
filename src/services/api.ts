import axios from 'axios';
import type { CaseItem, EvidenceItem, DashboardData, User } from '../types/investigation';

const rawApiUrl = import.meta.env.VITE_API_URL;
const API_BASE_URL = (rawApiUrl ? String(rawApiUrl).trim() : 'http://localhost:8000').replace(/\/+$/, '');

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for heavy OCR / LLM operations
});

const TOKEN_STORAGE_KEY = 'cyber_auth_token';
const USER_STORAGE_KEY = 'cyber_auth_user';

let onUnauthorizedHandler: (() => void) | null = null;

// Request interceptor: attach Bearer token to all outgoing requests
client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: intercept 401 Unauthorized
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(USER_STORAGE_KEY);
      if (onUnauthorizedHandler) {
        onUnauthorizedHandler();
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Session & Auth State Management
  setUnauthorizedHandler(handler: () => void) {
    onUnauthorizedHandler = handler;
  },

  getStoredToken(): string | null {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  },

  getStoredUser(): User | null {
    try {
      const raw = localStorage.getItem(USER_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  setSession(token: string, user: User) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  },

  clearSession() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
  },

  // Auth Endpoints
  async login(userId: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await client.post<{ access_token: string; user: User }>('/api/auth/login', {
      user_id: userId,
      password,
    });
    this.setSession(res.data.access_token, res.data.user);
    return res.data;
  },

  async logout(): Promise<void> {
    try {
      await client.post('/api/auth/logout');
    } catch {
      // Ignore network errors on logout
    } finally {
      this.clearSession();
    }
  },

  async getMe(): Promise<User> {
    const res = await client.get<User>('/api/auth/me');
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(res.data));
    return res.data;
  },

  async bootstrapAdmin(userId: string, password: string, displayName?: string, bootstrapKey?: string): Promise<{ access_token: string; user: User }> {
    const res = await client.post<{ access_token: string; user: User }>('/api/auth/bootstrap', {
      user_id: userId,
      password,
      display_name: displayName || 'Primary System Administrator',
      bootstrap_key: bootstrapKey || undefined,
    });
    this.setSession(res.data.access_token, res.data.user);
    return res.data;
  },

  // Admin User Management
  async listUsers(): Promise<User[]> {
    const res = await client.get<User[]>('/api/admin/users');
    return res.data;
  },

  async createUser(userId: string, password: string, displayName: string, role: 'admin' | 'investigator'): Promise<User> {
    const res = await client.post<User>('/api/admin/users', {
      user_id: userId,
      password,
      display_name: displayName,
      role,
    });
    return res.data;
  },

  async updateUser(userId: string, data: { display_name?: string; password?: string; role?: string; is_active?: boolean }): Promise<User> {
    const res = await client.patch<User>(`/api/admin/users/${userId}`, data);
    return res.data;
  },

  async reassignCase(caseId: string, ownerUserId: string): Promise<CaseItem> {
    const res = await client.patch<CaseItem>(`/api/admin/cases/${caseId}/reassign`, {
      owner_user_id: ownerUserId,
    });
    return res.data;
  },

  // Cases
  async listCases(): Promise<CaseItem[]> {
    const res = await client.get<CaseItem[]>('/api/cases');
    return res.data;
  },

  async getCase(caseId: string): Promise<CaseItem> {
    const res = await client.get<CaseItem>(`/api/cases/${caseId}`);
    return res.data;
  },

  async createCase(title: string, investigator?: string, description?: string): Promise<CaseItem> {
    const res = await client.post<CaseItem>('/api/cases', {
      title,
      investigator: investigator || 'Lead Cyber Investigator',
      description: description || 'Digital evidence investigation',
    });
    return res.data;
  },

  async deleteCase(caseId: string): Promise<void> {
    await client.delete(`/api/cases/${caseId}`);
  },

  // Evidence
  async listEvidence(caseId: string): Promise<EvidenceItem[]> {
    const res = await client.get<EvidenceItem[]>(`/api/cases/${caseId}/evidence`);
    return res.data;
  },

  async uploadEvidence(caseId: string, files: File[]): Promise<EvidenceItem[]> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const res = await client.post<EvidenceItem[]>(
      `/api/cases/${caseId}/evidence`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return res.data;
  },

  async deleteEvidence(caseId: string, evidenceId: string): Promise<void> {
    await client.delete(`/api/cases/${caseId}/evidence/${evidenceId}`);
  },

  // Analysis & Dashboard
  async analyzeCase(caseId: string): Promise<DashboardData> {
    const res = await client.post<DashboardData>(`/api/cases/${caseId}/analyze`);
    return res.data;
  },

  async getDashboard(caseId: string): Promise<DashboardData> {
    const res = await client.get<DashboardData>(`/api/cases/${caseId}/dashboard`);
    return res.data;
  },

  // Authenticated Report PDF Download via Blob
  async downloadReportPdf(caseId: string): Promise<void> {
    const res = await client.get(`/api/cases/${caseId}/report/pdf`, {
      responseType: 'blob',
    });
    const blob = new Blob([res.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Investigation_Report_${caseId}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
