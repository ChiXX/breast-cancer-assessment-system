export const getOrCreateSessionId = (): string => {
  let sessionId = localStorage.getItem('shenzhi_session_id');
  if (!sessionId) {
    sessionId = `session_${Math.random().toString(36).substring(2, 15)}`;
    localStorage.setItem('shenzhi_session_id', sessionId);
  }
  return sessionId;
};
