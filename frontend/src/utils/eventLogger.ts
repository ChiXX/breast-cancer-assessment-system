import axios from 'axios';
import { EventName } from '../types';

const API_BASE_URL = '/api/v1';

export const logEvent = async (
  eventName: EventName,
  sessionId: string,
  assessmentId?: number,
  metadata?: Record<string, any>
) => {
  try {
    await axios.post(`${API_BASE_URL}/events`, {
      event_name: eventName,
      session_id: sessionId,
      payload: {
        assessment_id: assessmentId,
        metadata: metadata || {},
      },
    });
  } catch (error) {
    console.error('Failed to log event:', error);
  }
};
