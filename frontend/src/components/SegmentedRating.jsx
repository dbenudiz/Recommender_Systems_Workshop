/**
 * SegmentedRating — a reusable 5-segment button row for rating an attribute.
 *
 * Props:
 *   label    {string}    — row label shown on the left (e.g. "Taste")
 *   labels   {string[5]} — text for each of the five segments
 *   value    {number}    — currently selected 1-5
 *   onChange {Function}  — called with the new numeric value when a segment is clicked
 */
const SegmentedRating = ({ label, labels, value, onChange }) => {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        marginBottom: '1rem',
      }}
    >
      <span
        style={{
          color: '#fff',
          fontWeight: 'bold',
          fontSize: '0.95rem',
          width: '100px',
          flexShrink: 0,
        }}
      >
        {label}
      </span>

      <div
        style={{
          display: 'flex',
          flex: 1,
          borderRadius: '6px',
          overflow: 'hidden',
          border: '1px solid #333',
        }}
      >
        {labels.map((segLabel, i) => {
          const segValue = i + 1;
          const isSelected = value === segValue;
          return (
            <button
              key={segValue}
              role="radio"
              aria-checked={isSelected}
              aria-label={`${label}: ${segLabel}`}
              onClick={() => onChange(segValue)}
              style={{
                flex: 1,
                padding: '0.5rem 0.2rem',
                fontSize: '0.72rem',
                fontWeight: isSelected ? 'bold' : 'normal',
                backgroundColor: isSelected ? '#E67E22' : '#1e1e1e',
                color: isSelected ? '#fff' : '#888',
                border: 'none',
                borderRight: i < labels.length - 1 ? '1px solid #333' : 'none',
                cursor: 'pointer',
                transition: 'background-color 0.15s, color 0.15s',
                textAlign: 'center',
                lineHeight: '1.3',
              }}
            >
              {segLabel}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SegmentedRating;
