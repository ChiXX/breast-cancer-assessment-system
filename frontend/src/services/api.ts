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
  submit: async (userInput: string, sessionId: string): Promise<Assessment> => {
    const response = await api.post('/assessments', {
      user_input: userInput,
      session_id: sessionId,
    });
    return response.data;
  },

  getById: async (id: number): Promise<Assessment> => {
    const response = await api.get(`/assessments/${id}`);
    return response.data;
  },

  getBySession: async (sessionId: string): Promise<Assessment[]> => {
    const response = await api.get('/assessments', {
      params: { session_id: sessionId }
    });
    return response.data;
  },
};
