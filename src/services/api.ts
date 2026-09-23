import axios from 'axios';
import type { CaseItem, EvidenceItem, DashboardData } from '../types/investigation';

const rawApiUrl = import.meta.env.VITE_API_URL;
const API_BASE_URL = (rawApiUrl ? String(rawApiUrl).trim() : 'http://localhost:8000').replace(/\/+$/, '');

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for heavy OCR / LLM operations
});

export const api = {
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

  // Report
  getReportPdfUrl(caseId: string): string {
    return `${API_BASE_URL}/api/cases/${caseId}/report/pdf`;
  },
};
