// Production upgrade path: swap Web Speech API for Google Cloud
// Text-to-Speech via the same FastAPI gateway. No UI changes needed.

import { useState, useCallback, useEffect, useRef } from 'react';
import { SPEECH_LANG_MAP } from '../i18n';

/**
 * Hook for browser-native speech synthesis (voice output).
 * Uses the Web Speech API (SpeechSynthesis).
 */
export function useSpeechSynthesis(language = 'hi') {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voices, setVoices] = useState([]);
  const utteranceRef = useRef(null);

  const isSupported =
    typeof window !== 'undefined' && 'speechSynthesis' in window;

  // Load available voices (async in some browsers)
  useEffect(() => {
    if (!isSupported) return;

    const loadVoices = () => {
      setVoices(window.speechSynthesis.getVoices());
    };

    loadVoices();
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);

    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', loadVoices);
    };
  }, [isSupported]);

  const speak = useCallback(
    (text) => {
      if (!isSupported || !text) return;

      // Cancel any ongoing speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      const langCode = SPEECH_LANG_MAP[language] || 'hi-IN';
      utterance.lang = langCode;

      // Try to find a matching voice
      const matchingVoice = voices.find((v) => v.lang === langCode);
      if (matchingVoice) {
        utterance.voice = matchingVoice;
      }

      utterance.rate = 0.9; // Slightly slower for clarity
      utterance.pitch = 1.0;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [language, voices, isSupported]
  );

  const stop = useCallback(() => {
    if (isSupported) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, [isSupported]);

  return { isSpeaking, speak, stop, isSupported };
}
