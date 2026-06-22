/**
 * MessageBubble — displays a single chat message (user or agent).
 * Supports text, images, and voice output via speak button.
 */
export default function MessageBubble({ message, agentLabel, onSpeak, isSpeaking }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message message--${isUser ? 'user' : 'agent'}`}>
      <div className="message__avatar">
        {isUser ? '👨‍🌾' : '🌾'}
      </div>
      <div>
        <div className="message__bubble">
          {message.isPhoto && message.imagePreview && (
            <img
              src={message.imagePreview}
              alt="Crop photo"
              style={{
                maxWidth: '100%',
                borderRadius: 12,
                marginBottom: 8,
                display: 'block',
              }}
            />
          )}
          {message.text}
        </div>
        <div className="message__meta">
          {agentLabel && (
            <span className="message__agent-badge">{agentLabel}</span>
          )}
          {!isUser && onSpeak && (
            <button
              onClick={onSpeak}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.85rem',
                padding: '2px 4px',
              }}
              title="Listen"
            >
              {isSpeaking ? '⏸️' : '🔊'}
            </button>
          )}
          <span style={{ fontSize: '0.65rem' }}>
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
      </div>
    </div>
  );
}
