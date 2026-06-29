/**
 * MethodChoiceScreen — full-screen centered layout presenting two onboarding paths.
 *
 * Props:
 *   onChooseMethod {Function} — called with 1 or 2 when user picks a method
 *   onSkip         {Function} — called when the user dismisses onboarding entirely
 */
const MethodChoiceScreen = ({ onChooseMethod, onSkip }) => {
  return (
    <div
      style={{
        backgroundColor: '#141414',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        color: '#fff',
      }}
    >
      <h1
        style={{
          fontSize: '2rem',
          fontWeight: 'bold',
          marginBottom: '0.5rem',
          textAlign: 'center',
        }}
      >
        Personalize your recommendations
      </h1>
      <p
        style={{
          color: '#aaa',
          marginBottom: '3rem',
          textAlign: 'center',
          fontSize: '1.1rem',
          maxWidth: '520px',
          lineHeight: '1.5',
        }}
      >
        Help us understand your taste so we can find the perfect beers for you.
      </p>

      {/* Card row */}
      <div
        style={{
          display: 'flex',
          gap: '2rem',
          flexWrap: 'wrap',
          justifyContent: 'center',
          maxWidth: '760px',
          width: '100%',
        }}
      >
        {/* Method 1 — recommended */}
        <div
          style={{
            flex: '1 1 300px',
            backgroundColor: '#1e1e1e',
            border: '2px solid #E67E22',
            borderRadius: '16px',
            padding: '2.5rem 2rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
            maxWidth: '340px',
            position: 'relative',
          }}
        >
          {/* Recommended badge */}
          <div
            style={{
              position: 'absolute',
              top: '-13px',
              backgroundColor: '#E67E22',
              color: '#fff',
              padding: '0.2rem 0.8rem',
              borderRadius: '12px',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              letterSpacing: '0.5px',
            }}
          >
            Recommended
          </div>

          {/* Beer icon */}
          <div style={{ fontSize: '3rem', marginTop: '0.5rem' }}>
            <svg
              width="52"
              height="52"
              viewBox="0 0 24 24"
              fill="#E67E22"
              stroke="#E67E22"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M10 2v5l-2 3v10a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-10l-2-3V2z" />
              <path d="M10 2h4" />
            </svg>
          </div>

          <h2
            style={{
              margin: 0,
              fontSize: '1.3rem',
              color: '#fff',
              textAlign: 'center',
            }}
          >
            Rate beers you know
          </h2>
          <p
            style={{
              color: '#aaa',
              textAlign: 'center',
              margin: 0,
              fontSize: '0.95rem',
              lineHeight: '1.5',
            }}
          >
            Search real beers and rate them. Best results.
          </p>

          <button
            onClick={() => onChooseMethod(1)}
            style={{
              marginTop: '0.5rem',
              backgroundColor: '#E67E22',
              color: '#fff',
              border: 'none',
              padding: '0.85rem 2rem',
              borderRadius: '8px',
              fontWeight: 'bold',
              fontSize: '1rem',
              cursor: 'pointer',
              width: '100%',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#d67118'; }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#E67E22'; }}
          >
            Get started &rarr;
          </button>
        </div>

        {/* Method 2 */}
        <div
          style={{
            flex: '1 1 300px',
            backgroundColor: '#1e1e1e',
            border: '2px solid #333',
            borderRadius: '16px',
            padding: '2.5rem 2rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
            maxWidth: '340px',
          }}
        >
          {/* Sliders icon */}
          <div style={{ marginTop: '0.5rem' }}>
            <svg
              width="52"
              height="52"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#888"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="18" x2="20" y2="18" />
              <circle cx="8" cy="6" r="2" fill="#888" stroke="#888" />
              <circle cx="16" cy="12" r="2" fill="#888" stroke="#888" />
              <circle cx="10" cy="18" r="2" fill="#888" stroke="#888" />
            </svg>
          </div>

          <h2
            style={{
              margin: 0,
              fontSize: '1.3rem',
              color: '#fff',
              textAlign: 'center',
            }}
          >
            Rate by what matters
          </h2>
          <p
            style={{
              color: '#aaa',
              textAlign: 'center',
              margin: 0,
              fontSize: '0.95rem',
              lineHeight: '1.5',
            }}
          >
            Score taste, aroma, and more. Takes ~45 seconds.
          </p>

          <button
            onClick={() => onChooseMethod(2)}
            style={{
              marginTop: 'auto',
              backgroundColor: 'transparent',
              color: '#E67E22',
              border: '2px solid #E67E22',
              padding: '0.85rem 2rem',
              borderRadius: '8px',
              fontWeight: 'bold',
              fontSize: '1rem',
              cursor: 'pointer',
              width: '100%',
              transition: 'background-color 0.2s, color 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#E67E22';
              e.currentTarget.style.color = '#fff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = '#E67E22';
            }}
          >
            Get started &rarr;
          </button>
        </div>
      </div>

      {/* Skip link */}
      <button
        onClick={onSkip}
        style={{
          marginTop: '2.5rem',
          background: 'none',
          border: 'none',
          color: '#555',
          fontSize: '0.9rem',
          cursor: 'pointer',
          textDecoration: 'underline',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.color = '#888'; }}
        onMouseLeave={(e) => { e.currentTarget.style.color = '#555'; }}
      >
        Skip for now &mdash; I&apos;ll rate beers as I go
      </button>
    </div>
  );
};

export default MethodChoiceScreen;
