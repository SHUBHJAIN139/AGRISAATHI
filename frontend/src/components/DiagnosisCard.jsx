/**
 * DiagnosisCard — glassmorphism card showing crop disease diagnosis results.
 * Displays disease name, confidence, severity, treatments (organic first).
 */
export default function DiagnosisCard({ diagnosis, language, onSpeak }) {
  const {
    disease,
    confidence,
    crop_name,
    treatment,
    organic_alternative,
    organic_treatment,
    severity,
  } = diagnosis;

  const confidencePercent = Math.round((confidence || 0) * 100);
  const confidenceClass =
    confidencePercent >= 80 ? 'high' : confidencePercent >= 50 ? 'medium' : 'low';
  const severityClass = severity || 'medium';

  const isHindi = language === 'hi';

  return (
    <div className="message message--agent">
      <div className="message__avatar">🔬</div>
      <div className="diagnosis-card" id="diagnosis-card">
        <div className="diagnosis-card__header">
          <span className="diagnosis-card__disease">
            {disease?.replace(/_/g, ' ') || 'Unknown'}
          </span>
          <span className={`diagnosis-card__confidence confidence--${confidenceClass}`}>
            {confidencePercent}%
          </span>
        </div>

        <div className="diagnosis-card__crop">
          {isHindi ? '🌿 फसल: ' : '🌿 Crop: '}
          <strong>{crop_name || 'Unknown'}</strong>
        </div>

        <span className={`diagnosis-card__severity severity--${severityClass}`}>
          ⚠️ {isHindi ? 'गंभीरता: ' : 'Severity: '}
          {severity}
        </span>

        {organic_alternative && organic_treatment && (
          <div className="diagnosis-card__section">
            <div className="diagnosis-card__section-title">
              🌱 {isHindi ? 'जैविक उपचार (पहले आज़माएं)' : 'Organic Treatment (try first)'}
            </div>
            <div className="diagnosis-card__section-text">{organic_treatment}</div>
          </div>
        )}

        <div className="diagnosis-card__section">
          <div className="diagnosis-card__section-title">
            💊 {isHindi ? 'रासायनिक उपचार' : 'Chemical Treatment'}
          </div>
          <div className="diagnosis-card__section-text">{treatment}</div>
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <span className="message__agent-badge">🔬 CropDoctor</span>
          {onSpeak && (
            <button
              onClick={onSpeak}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.85rem',
              }}
              title="Listen"
            >
              🔊
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
