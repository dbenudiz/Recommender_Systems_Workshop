export default function NewUserBanner({ onDismiss }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: 'rgba(230, 126, 34, 0.12)',
      border: '1px solid rgba(230, 126, 34, 0.3)',
      borderRadius: '8px',
      padding: '12px 16px',
      marginBottom: '16px',
      color: '#ccc',
      fontSize: '14px',
    }}>
      <span>
        Your recommendations improve as you rate more beers.{' '}
        <span style={{ color: '#E67E22' }}>Rate anything in your feed</span> to teach us your taste.
      </span>
      <button
        onClick={onDismiss}
        aria-label="Dismiss banner"
        style={{
          background: 'none',
          border: 'none',
          color: '#888',
          cursor: 'pointer',
          fontSize: '18px',
          padding: '0 0 0 12px',
          lineHeight: 1,
        }}
      >
        &times;
      </button>
    </div>
  );
}
