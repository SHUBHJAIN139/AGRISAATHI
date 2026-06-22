import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { LANGUAGE_LABELS } from './i18n';
import { useChat } from './hooks/useChat';
import { useSpeechRecognition } from './hooks/useSpeechRecognition';
import { useSpeechSynthesis } from './hooks/useSpeechSynthesis';
import MessageBubble from './components/MessageBubble';
import DiagnosisCard from './components/DiagnosisCard';
import PhotoCapture from './components/PhotoCapture';

const AGENT_LABELS = {
  farmer_concierge: '🌾 AgriSaathi',
  crop_doctor: '🔬 CropDoctor',
  weather_advisor: '🌤️ WeatherAdvisor',
  market_whisperer: '📊 MarketWhisperer',
  scheme_guide: '🏛️ SchemeGuide',
};

export default function App() {
  const { i18n, t } = useTranslation();
  const [inputText, setInputText] = useState('');
  const [showCamera, setShowCamera] = useState(false);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const currentLang = i18n.language?.slice(0, 2) || 'hi';
  const { messages, isLoading, sendMessage, sendPhoto, clearMessages } = useChat();
  const speech = useSpeechRecognition(currentLang);
  const synthesis = useSpeechSynthesis(currentLang);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // When speech recognition captures text, put it in the input
  useEffect(() => {
    if (speech.transcript) {
      setInputText(speech.transcript);
    }
  }, [speech.transcript]);

  const handleSend = useCallback(() => {
    if (!inputText.trim() || isLoading) return;
    sendMessage(inputText, currentLang);
    setInputText('');
    inputRef.current?.focus();
  }, [inputText, isLoading, sendMessage, currentLang]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handlePhotoCapture = useCallback(
    (imageBase64, filename) => {
      setShowCamera(false);
      sendPhoto(imageBase64, filename, currentLang);
    },
    [sendPhoto, currentLang]
  );

  const handleVoiceToggle = useCallback(() => {
    if (speech.isListening) {
      speech.stopListening();
    } else {
      speech.startListening();
    }
  }, [speech]);

  const handleLanguageChange = useCallback(
    (lang) => {
      i18n.changeLanguage(lang);
    },
    [i18n]
  );

  const handleFeatureClick = useCallback(
    (prompt) => {
      sendMessage(prompt, currentLang);
    },
    [sendMessage, currentLang]
  );

  // Speak the last agent message
  const handleSpeak = useCallback(
    (text) => {
      if (synthesis.isSpeaking) {
        synthesis.stop();
      } else {
        // Strip markdown/emoji for cleaner speech
        const clean = text.replace(/[*#🌿🔬📊⚠️💊🌱📅💧📈💡🏛️📋✅📄📞🌐🙏🌾🍅☀️🌤️🌧️🏪]/g, '').trim();
        synthesis.speak(clean);
      }
    },
    [synthesis]
  );

  const hasMessages = messages.length > 0;

  return (
    <>
      {/* Header */}
      <header className="header" id="app-header">
        <div className="header__logo">
          <div className="header__icon">🌾</div>
          <div>
            <div className="header__title">AgriSaathi</div>
            <div className="header__subtitle">अन्नदाता साथी</div>
          </div>
        </div>
        {hasMessages && (
          <button
            className="input-area__btn input-area__btn--camera"
            onClick={clearMessages}
            title="New conversation"
            style={{ width: 36, height: 36, fontSize: '0.9rem' }}
            id="btn-new-chat"
          >
            ✨
          </button>
        )}
      </header>

      {/* Language Selector */}
      <div className="lang-selector" id="language-selector">
        {Object.entries(LANGUAGE_LABELS).map(([code, label]) => (
          <button
            key={code}
            className={`lang-btn ${currentLang === code ? 'lang-btn--active' : ''}`}
            onClick={() => handleLanguageChange(code)}
            id={`lang-btn-${code}`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Chat Area */}
      <div className="chat-window" id="chat-window">
        {!hasMessages ? (
          <div className="welcome" id="welcome-screen">
            <div className="welcome__icon">🌾</div>
            <h1 className="welcome__title">
              {currentLang === 'hi'
                ? 'नमस्ते! मैं अन्नदाता साथी हूँ'
                : currentLang === 'ta'
                  ? 'வணக்கம்! நான் அக்ரிசாதி'
                  : currentLang === 'te'
                    ? 'నమస్కారం! నేను అగ్రిసాతి'
                    : currentLang === 'bn'
                      ? 'নমস্কার! আমি অগ্রিসাথী'
                      : currentLang === 'mr'
                        ? 'नमस्कार! मी अग्रीसाथी'
                        : 'Namaste! I am AgriSaathi'}
            </h1>
            <p className="welcome__subtitle">
              {currentLang === 'hi'
                ? 'आपकी खेती में AI साथी। फोटो, मौसम, भाव, योजनाएं — सब एक जगह।'
                : 'Your AI farming companion. Photos, weather, prices, schemes — all in one place.'}
            </p>
            <div className="welcome__features">
              <div
                className="welcome__feature"
                onClick={() =>
                  handleFeatureClick(
                    currentLang === 'hi'
                      ? 'मेरे टमाटर के पत्ते पीले हो रहे हैं'
                      : 'My tomato leaves are turning yellow'
                  )
                }
                id="feature-disease"
              >
                <span className="welcome__feature-icon">📸</span>
                <span>
                  {currentLang === 'hi'
                    ? 'फसल रोग पहचान'
                    : 'Crop Disease Diagnosis'}
                </span>
              </div>
              <div
                className="welcome__feature"
                onClick={() =>
                  handleFeatureClick(
                    currentLang === 'hi'
                      ? 'आज मौसम कैसा रहेगा? सिंचाई करूँ?'
                      : 'How is the weather today? Should I irrigate?'
                  )
                }
                id="feature-weather"
              >
                <span className="welcome__feature-icon">🌤️</span>
                <span>
                  {currentLang === 'hi'
                    ? 'मौसम और सिंचाई सलाह'
                    : 'Weather & Irrigation Advice'}
                </span>
              </div>
              <div
                className="welcome__feature"
                onClick={() =>
                  handleFeatureClick(
                    currentLang === 'hi'
                      ? 'टमाटर का आज मंडी भाव क्या है?'
                      : 'What is today\'s tomato market price?'
                  )
                }
                id="feature-price"
              >
                <span className="welcome__feature-icon">📊</span>
                <span>
                  {currentLang === 'hi' ? 'मंडी भाव' : 'Mandi Prices'}
                </span>
              </div>
              <div
                className="welcome__feature"
                onClick={() =>
                  handleFeatureClick(
                    currentLang === 'hi'
                      ? 'मुझे सरकारी योजनाओं के बारे में बताओ'
                      : 'Tell me about government schemes'
                  )
                }
                id="feature-schemes"
              >
                <span className="welcome__feature-icon">🏛️</span>
                <span>
                  {currentLang === 'hi'
                    ? 'सरकारी योजनाएं'
                    : 'Government Schemes'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id}>
                {msg.diagnosis ? (
                  <DiagnosisCard
                    diagnosis={msg.diagnosis}
                    language={currentLang}
                    onSpeak={() => handleSpeak(
                      `${msg.diagnosis.disease}. ${msg.diagnosis.treatment}`
                    )}
                  />
                ) : (
                  <MessageBubble
                    message={msg}
                    agentLabel={msg.agent ? AGENT_LABELS[msg.agent] : null}
                    onSpeak={
                      msg.role === 'agent' ? () => handleSpeak(msg.text) : null
                    }
                    isSpeaking={synthesis.isSpeaking}
                  />
                )}
              </div>
            ))}
            {isLoading && (
              <div className="typing-indicator" id="typing-indicator">
                <div className="typing-dots">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
                <span className="typing-label">
                  {currentLang === 'hi' ? 'सोच रहा हूँ...' : 'Thinking...'}
                </span>
              </div>
            )}
            <div ref={chatEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="input-area" id="input-area">
        <button
          className="input-area__btn input-area__btn--camera"
          onClick={() => setShowCamera(true)}
          title="Take photo for diagnosis"
          id="btn-camera"
        >
          📷
        </button>
        <button
          className={`input-area__btn input-area__btn--voice ${
            speech.isListening ? 'recording' : ''
          }`}
          onClick={handleVoiceToggle}
          title={speech.isListening ? 'Stop recording' : 'Voice input'}
          disabled={!speech.isSupported}
          id="btn-voice"
        >
          🎤
        </button>
        <input
          ref={inputRef}
          className="input-area__field"
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            currentLang === 'hi'
              ? 'अपना सवाल लिखें...'
              : currentLang === 'ta'
                ? 'உங்கள் கேள்வியை தட்டச்சு செய்யுங்கள்...'
                : 'Type your question...'
          }
          disabled={isLoading}
          id="chat-input"
        />
        <button
          className="input-area__btn input-area__btn--send"
          onClick={handleSend}
          disabled={!inputText.trim() || isLoading}
          title="Send"
          id="btn-send"
        >
          ➤
        </button>
      </div>

      {/* Photo Capture Modal */}
      {showCamera && (
        <PhotoCapture
          onCapture={handlePhotoCapture}
          onClose={() => setShowCamera(false)}
          language={currentLang}
        />
      )}
    </>
  );
}
