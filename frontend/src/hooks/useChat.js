import { useState, useCallback, useRef } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Hook for chat interactions with the AgriSaathi API.
 * Manages message history, loading state, and API calls.
 */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const sessionIdRef = useRef(`session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`);
  const tokenRef = useRef(null);

  /** Get or create a dev JWT token */
  const getToken = useCallback(async () => {
    if (tokenRef.current) return tokenRef.current;
    try {
      const res = await fetch(`${API_URL}/token?user_id=farmer_demo`, {
        method: 'POST',
      });
      const data = await res.json();
      tokenRef.current = data.token;
      return data.token;
    } catch {
      // Fallback: use a placeholder token for demo
      return 'demo-token';
    }
  }, []);

  /** Send a text message to the chat API */
  const sendMessage = useCallback(
    async (text, language = 'hi') => {
      if (!text.trim()) return;

      // Add user message to history
      const userMsg = {
        id: Date.now(),
        role: 'user',
        text: text.trim(),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      try {
        const token = await getToken();
        const res = await fetch(`${API_URL}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            message: text.trim(),
            session_id: sessionIdRef.current,
            user_id: 'farmer_demo',
            language,
          }),
        });

        if (!res.ok) throw new Error(`API error: ${res.status}`);

        const data = await res.json();

        const agentMsg = {
          id: Date.now() + 1,
          role: 'agent',
          text: data.response,
          agent: data.agent_used,
          timestamp: data.timestamp || new Date().toISOString(),
        };
        setMessages((prev) => [...prev, agentMsg]);
      } catch (err) {
        setError(err.message);
        // Add fallback message
        const fallback = {
          id: Date.now() + 1,
          role: 'agent',
          text: 'कनेक्शन में समस्या है। कृपया पुनः प्रयास करें। (Connection issue. Please try again.)',
          agent: 'farmer_concierge',
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, fallback]);
      } finally {
        setIsLoading(false);
      }
    },
    [getToken]
  );

  /** Send a photo for diagnosis */
  const sendPhoto = useCallback(
    async (imageBase64, filename = null, language = 'hi') => {
      const userMsg = {
        id: Date.now(),
        role: 'user',
        text: '📸 [Photo sent for diagnosis]',
        isPhoto: true,
        imagePreview: imageBase64.startsWith('data:')
          ? imageBase64
          : `data:image/jpeg;base64,${imageBase64}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      try {
        const token = await getToken();
        // Strip data URL prefix if present
        const base64Data = imageBase64.includes(',')
          ? imageBase64.split(',')[1]
          : imageBase64;

        const res = await fetch(`${API_URL}/diagnose`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            image_base64: base64Data,
            image_filename: filename,
            session_id: sessionIdRef.current,
            user_id: 'farmer_demo',
            language,
          }),
        });

        if (!res.ok) throw new Error(`API error: ${res.status}`);

        const data = await res.json();

        const agentMsg = {
          id: Date.now() + 1,
          role: 'agent',
          text: null,
          agent: 'crop_doctor',
          diagnosis: data,
          timestamp: data.timestamp || new Date().toISOString(),
        };
        setMessages((prev) => [...prev, agentMsg]);
      } catch (err) {
        setError(err.message);
        const fallback = {
          id: Date.now() + 1,
          role: 'agent',
          text: 'फोटो विश्लेषण में त्रुटि। पुनः प्रयास करें। (Photo analysis error. Please retry.)',
          agent: 'crop_doctor',
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, fallback]);
      } finally {
        setIsLoading(false);
      }
    },
    [getToken]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    sendPhoto,
    clearMessages,
    sessionId: sessionIdRef.current,
  };
}
