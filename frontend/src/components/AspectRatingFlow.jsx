import { useState } from 'react';
import SegmentedRating from './SegmentedRating';

/**
 * AspectRatingFlow — Method 2 cold-start flow.
 * Users rate taste/aroma/appearance/palate, pick an ABV preference,
 * and select at least one beer style. All defaults are valid so the
 * form can always be submitted (styles are validated on click).
 *
 * Props:
 *   onComplete {Function} — called with { taste, aroma, appearance, palate, abv_pref, styles }
 *   onBack     {Function} — navigate back to the choice screen
 */

const ASPECT_LABELS = ['Not important', 'Slight', 'Balanced', 'Important', 'Essential'];

const ABV_OPTIONS = [
  { value: 'light',  label: 'Light ≤4%' },
  { value: 'medium', label: 'Medium 4–7%' },
  { value: 'strong', label: 'Strong 7%+' },
  { value: 'any',    label: 'No preference' },
];

// Style options defined inline — OnboardingPage.jsx does not export STYLE_OPTIONS.
// The id values use beer_style strings present in item_profiles.
const STYLE_OPTIONS = [
  { id: 'IPA',        label: 'IPA' },
  { id: 'Stout',      label: 'Stout' },
  { id: 'Lager',      label: 'Lager' },
  { id: 'Sour Ale',   label: 'Sour Ale' },
  { id: 'Pale Ale',   label: 'Pale Ale' },
  { id: 'Wheat Beer', label: 'Wheat Beer' },
  { id: 'Porter',     label: 'Porter' },
  { id: 'Pilsner',    label: 'Pilsner' },
];

const AspectRatingFlow = ({ onComplete, onBack }) => {
  const [taste,      setTaste]      = useState(3);
  const [aroma,      setAroma]      = useState(3);
  const [appearance, setAppearance] = useState(3);
  const [palate,     setPalate]     = useState(3);
  const [abvPref,    setAbvPref]    = useState('any');
  const [selectedStyles, setSelectedStyles] = useState([]);
  const [styleError, setStyleError] = useState(false);

  const toggleStyle = (id) => {
    setStyleError(false);
    setSelectedStyles((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const handleContinue = () => {
    if (selectedStyles.length === 0) {
      setStyleError(true);
      return;
    }
    onComplete({
      taste,
      aroma,
      appearance,
      palate,
      abv_pref: abvPref,
      styles: selectedStyles,
    });
  };

  const chipStyle = (isActive) => ({
    padding: '0.5rem 1rem',
    borderRadius: '20px',
    border: `1px solid ${isActive ? '#E67E22' : '#444'}`,
    backgroundColor: isActive ? '#E67E22' : 'transparent',
    color: isActive ? '#fff' : '#aaa',
    fontWeight: isActive ? 'bold' : 'normal',
    cursor: 'pointer',
    fontSize: '0.9rem',
    transition: 'all 0.15s',
  });

  return (
    <div
      style={{
        backgroundColor: '#141414',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '2rem',
        color: '#fff',
      }}
    >
      <div style={{ width: '100%', maxWidth: '520px' }}>
        {/* Back */}
        <button
          onClick={onBack}
          style={{
            background: 'none',
            border: 'none',
            color: '#E67E22',
            fontSize: '1rem',
            cursor: 'pointer',
            marginBottom: '1.5rem',
            fontWeight: 'bold',
            padding: 0,
          }}
        >
          &larr; Back
        </button>

        <h1 style={{ fontSize: '1.8rem', fontWeight: 'bold', marginBottom: '0.25rem' }}>
          Rate what matters to you in a beer
        </h1>
        <p style={{ color: '#aaa', marginBottom: '2rem', fontSize: '1rem' }}>
          Help us understand your taste.
        </p>

        {/* ---- Aspect sliders ---- */}
        <div
          style={{
            backgroundColor: '#1e1e1e',
            border: '1px solid #2a2a2a',
            borderRadius: '12px',
            padding: '1.5rem',
            marginBottom: '1.5rem',
          }}
        >
          <SegmentedRating
            label="Taste"
            labels={ASPECT_LABELS}
            value={taste}
            onChange={setTaste}
          />
          <SegmentedRating
            label="Aroma"
            labels={ASPECT_LABELS}
            value={aroma}
            onChange={setAroma}
          />
          <SegmentedRating
            label="Appearance"
            labels={ASPECT_LABELS}
            value={appearance}
            onChange={setAppearance}
          />
          <SegmentedRating
            label="Palate"
            labels={ASPECT_LABELS}
            value={palate}
            onChange={setPalate}
          />
        </div>

        {/* ---- ABV preference ---- */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3
            style={{
              color: '#fff',
              marginBottom: '0.75rem',
              fontSize: '1rem',
              fontWeight: 'bold',
            }}
          >
            Alcohol strength
          </h3>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {ABV_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setAbvPref(opt.value)}
                style={chipStyle(abvPref === opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* ---- Style chips ---- */}
        <div style={{ marginBottom: '2rem' }}>
          <h3
            style={{
              color: '#fff',
              marginBottom: '0.25rem',
              fontSize: '1rem',
              fontWeight: 'bold',
              display: 'flex',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.5rem',
            }}
          >
            Which styles do you enjoy?
            {styleError && (
              <span style={{ color: '#ff4d4d', fontSize: '0.82rem', fontWeight: 'normal' }}>
                Please select at least one style
              </span>
            )}
          </h3>
          <p style={{ color: '#666', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
            Select all that apply
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {STYLE_OPTIONS.map((style) => (
              <button
                key={style.id}
                onClick={() => toggleStyle(style.id)}
                style={chipStyle(selectedStyles.includes(style.id))}
              >
                {style.label}
              </button>
            ))}
          </div>
        </div>

        {/* ---- Continue button ---- */}
        <button
          onClick={handleContinue}
          style={{
            width: '100%',
            padding: '1rem',
            backgroundColor: '#E67E22',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            fontWeight: 'bold',
            fontSize: '1.05rem',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#d67118'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#E67E22'; }}
        >
          Build my recommendations &rarr;
        </button>
      </div>
    </div>
  );
};

export default AspectRatingFlow;
