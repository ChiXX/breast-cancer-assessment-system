import axios from 'axios';
import type { Assessment } from '../types';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const assessmentService = {
  submit: async (userInput: string, sessionId: string, history?: {role: string, content: string}[]): Promise<Assessment> => {
    const response = await api.post('/assessments', {
      user_input: userInput,
      session_id: sessionId,
      history: history,
    });
    return response.data;
  },

  getById: async (id: number): Promise<Assessment> => {
    const response = await api.get(`/assessments/${id}`);
    return response.data;
  },

  getAll: async (sessionId?: string): Promise<Assessment[]> => {
    const response = await api.get('/assessments', {
      params: { session_id: sessionId }
    });
    return response.data;
  },

  getBySession: async (sessionId: string): Promise<any[]> => {
    const response = await api.get('/assessments/history', {
      params: { session_id: sessionId }
    });
    return response.data;
  },

  getHistory: async (id: number): Promise<{role: string, content: string}[]> => {
    const response = await api.get(`/assessments/${id}/history`);
    return response.data;
  },

  save: async (sessionId: string, assessment: Assessment, history: {role: string, content: string}[]): Promise<Assessment> => {
    const response = await api.post('/assessments/save', {
      session_id: sessionId,
      assessment: assessment,
      history: history,
    });
    return response.data;
  },
};
