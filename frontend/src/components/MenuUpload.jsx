import React, { useState, useRef } from 'react';
import { uploadMenuImage } from '../services/apiService';

// Props: { userId, onClose, onResults }
// onResults(data) is called with the raw API response on success
const MenuUpload = ({ userId, onClose, onResults }) => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const handleFile = (f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleSubmit = async () => {
    if (!file || loading) return;
    setLoading(true);
    setError(null);
    try {
      const data = await uploadMenuImage(userId, file, 10);
      onClose();
      onResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={onClose}
    >
      <div
        style={{
          maxWidth: '480px',
          width: '90%',
          margin: 'auto',
          background: '#1a1a1a',
          borderRadius: '12px',
          padding: '2rem',
          boxSizing: 'border-box',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ margin: 0, color: '#fff' }}>Scan Menu</h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#fff', fontSize: '1.5rem', cursor: 'pointer', lineHeight: 1, padding: 0 }}
          >
            &times;
          </button>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          style={{
            border: `2px dashed ${isDragging ? '#E67E22' : '#444'}`,
            borderRadius: '8px',
            padding: '2rem',
            textAlign: 'center',
            cursor: 'pointer',
            backgroundColor: isDragging ? 'rgba(230,126,34,0.08)' : '#111',
            transition: 'border-color 0.2s, background-color 0.2s',
            marginBottom: '1rem',
            minHeight: '160px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {preview ? (
            <img
              src={preview}
              alt="Menu preview"
              style={{ maxWidth: '100%', maxHeight: '200px', borderRadius: '6px', objectFit: 'contain' }}
            />
          ) : (
            <>
              <div style={{ marginBottom: '0.8rem', color: '#E67E22' }}>
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </div>
              <p style={{ color: '#aaa', margin: 0, fontSize: '0.95rem' }}>
                Drag &amp; drop a menu photo here, or click to browse
              </p>
            </>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={(e) => handleFile(e.target.files[0])}
        />

        {error && (
          <p style={{ color: '#ff4d4d', margin: '0 0 1rem 0', fontSize: '0.9rem' }}>{error}</p>
        )}

        <button
          onClick={handleSubmit}
          disabled={!file || loading}
          style={{
            width: '100%',
            padding: '0.9rem',
            backgroundColor: !file || loading ? '#333' : '#E67E22',
            color: !file || loading ? '#666' : '#fff',
            border: 'none',
            borderRadius: '8px',
            fontWeight: 'bold',
            fontSize: '1rem',
            cursor: !file || loading ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s',
          }}
        >
          {loading ? 'Scanning menu...' : 'Scan Menu'}
        </button>
      </div>
    </div>
  );
};

export default MenuUpload;
