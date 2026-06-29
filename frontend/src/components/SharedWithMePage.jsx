import { useState, useEffect } from 'react';
import { getUserRecord, markSharesSeen } from '../services/authService';

const timeAgo = (ts) => {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
};

const SharedWithMePage = ({ userId, onBeerClick }) => {
  const [shares, setShares] = useState([]);

  useEffect(() => {
    if (!userId) return;
    const record = getUserRecord(userId);
    const list = [...(record?.sharedWithMe || [])].reverse();
    setShares(list);
    markSharesSeen(userId);
  }, [userId]);

  if (!userId) {
    return (
      <div style={{ padding: '4rem 2rem', textAlign: 'center', color: '#aaa' }}>
        <p style={{ fontSize: '1.1rem' }}>Sign in to share beers with friends.</p>
      </div>
    );
  }

  if (shares.length === 0) {
    return (
      <div style={{ padding: '4rem 2rem', textAlign: 'center', color: '#aaa' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🍺</div>
        <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Nothing here yet.</p>
        <p style={{ fontSize: '0.9rem' }}>When a friend shares a beer with you, it'll show up here.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '680px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <h2 style={{ color: '#fff', marginBottom: '1.25rem', fontSize: '1.4rem' }}>
        Shared With Me
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {shares.map((share) => (
          <div
            key={share.id}
            onClick={() => onBeerClick(share.beerId)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              backgroundColor: '#1e1e1e',
              border: `1px solid ${share.seen ? '#2a2a2a' : '#E67E22'}`,
              borderRadius: '10px',
              padding: '0.9rem 1rem',
              cursor: 'pointer',
              transition: 'background-color 0.15s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#252525'; }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#1e1e1e'; }}
          >
            <img
              src={share.beerImage}
              alt={share.beerName}
              style={{ width: '56px', height: '56px', objectFit: 'cover', borderRadius: '6px', flexShrink: 0 }}
            />

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 'bold', color: '#fff', fontSize: '1rem' }}>
                  {share.beerName}
                </span>
                {!share.seen && (
                  <span style={{
                    backgroundColor: '#E67E22', color: '#fff',
                    fontSize: '0.65rem', fontWeight: 'bold',
                    padding: '0.1rem 0.45rem', borderRadius: '99px',
                  }}>
                    NEW
                  </span>
                )}
              </div>
              <div style={{ color: '#888', fontSize: '0.82rem', marginTop: '0.1rem' }}>
                {share.beerStyle}{share.beerAbv ? ` · ${share.beerAbv}% ABV` : ''}
              </div>
              {share.note && (
                <div style={{
                  marginTop: '0.4rem', color: '#ccc', fontSize: '0.87rem',
                  fontStyle: 'italic',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  "{share.note}"
                </div>
              )}
            </div>

            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ color: '#E67E22', fontSize: '0.82rem', fontWeight: 'bold' }}>
                {share.sharedByName}
              </div>
              <div style={{ color: '#555', fontSize: '0.75rem', marginTop: '0.15rem' }}>
                {timeAgo(share.sharedAt)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SharedWithMePage;
