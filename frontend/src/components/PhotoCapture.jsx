import { useState, useRef, useCallback } from 'react';

/**
 * PhotoCapture — modal for taking or uploading crop leaf photos.
 * Supports both camera capture (mobile) and file upload (desktop).
 */
export default function PhotoCapture({ onCapture, onClose, language }) {
  const [preview, setPreview] = useState(null);
  const [fileName, setFileName] = useState(null);
  const fileInputRef = useRef(null);
  const isHindi = language === 'hi';

  const handleFileChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => {
      setPreview(ev.target.result);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleAnalyze = useCallback(() => {
    if (preview) {
      onCapture(preview, fileName);
    }
  }, [preview, fileName, onCapture]);

  return (
    <div className="photo-modal" id="photo-modal">
      {!preview ? (
        <>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: 16 }}>📸</div>
            <h2 style={{ color: 'var(--color-text-primary)', marginBottom: 8 }}>
              {isHindi ? 'फसल का फोटो लें' : 'Take a Crop Photo'}
            </h2>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: 24, fontSize: '0.9rem' }}>
              {isHindi
                ? 'पत्ते का करीबी फोटो लें। अच्छी रोशनी में।'
                : 'Take a close-up of the affected leaf. Good lighting helps.'}
            </p>
          </div>
          <div className="photo-modal__actions">
            <button
              className="photo-modal__btn photo-modal__btn--analyze"
              onClick={() => fileInputRef.current?.click()}
              id="btn-take-photo"
            >
              {isHindi ? '📷 फोटो लें / चुनें' : '📷 Take / Choose Photo'}
            </button>
            <button
              className="photo-modal__btn photo-modal__btn--cancel"
              onClick={onClose}
              id="btn-cancel-photo"
            >
              {isHindi ? 'रद्द करें' : 'Cancel'}
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
            style={{ display: 'none' }}
            id="file-input"
          />
        </>
      ) : (
        <>
          <img
            src={preview}
            alt="Crop leaf preview"
            className="photo-modal__preview"
            id="photo-preview"
          />
          <div className="photo-modal__actions">
            <button
              className="photo-modal__btn photo-modal__btn--analyze"
              onClick={handleAnalyze}
              id="btn-analyze-photo"
            >
              {isHindi ? '🔬 विश्लेषण करें' : '🔬 Analyze'}
            </button>
            <button
              className="photo-modal__btn photo-modal__btn--cancel"
              onClick={() => {
                setPreview(null);
                setFileName(null);
              }}
              id="btn-retake-photo"
            >
              {isHindi ? 'दोबारा लें' : 'Retake'}
            </button>
            <button
              className="photo-modal__btn photo-modal__btn--cancel"
              onClick={onClose}
              id="btn-close-photo"
            >
              ✕
            </button>
          </div>
        </>
      )}
    </div>
  );
}
