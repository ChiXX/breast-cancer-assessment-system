export const getOrCreateSessionId = (): string => {
  let sessionId = localStorage.getItem('shenzhi_session_id');
  if (!sessionId) {
    return createNewSessionId();
  }
  return sessionId;
};

export const createNewSessionId = (): string => {
  const sessionId = `session_${Math.random().toString(36).substring(2, 15)}`;
  localStorage.setItem('shenzhi_session_id', sessionId);
  return sessionId;
};
