import { useState, useEffect } from 'react';
import { getUserRecord, updateDisplayName, updatePassword } from '../services/authService';

const Section = ({ title, children }) => (
  <div style={{
    backgroundColor: '#1e1e1e',
    border: '1px solid #2a2a2a',
    borderRadius: '10px',
    padding: '1.5rem',
    marginBottom: '1.25rem',
  }}>
    <h3 style={{ margin: '0 0 1rem', color: '#E67E22', fontSize: '1rem', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
      {title}
    </h3>
    {children}
  </div>
);

const Feedback = ({ msg, isError }) =>
  msg ? (
    <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: isError ? '#e74c3c' : '#2ecc71' }}>
      {msg}
    </p>
  ) : null;

const inputStyle = {
  width: '100%',
  backgroundColor: '#141414',
  border: '1px solid #333',
  borderRadius: '6px',
  color: '#fff',
  padding: '0.65rem 0.8rem',
  fontSize: '0.95rem',
  boxSizing: 'border-box',
  outline: 'none',
};

const btnStyle = (disabled) => ({
  marginTop: '0.75rem',
  padding: '0.6rem 1.5rem',
  backgroundColor: disabled ? '#333' : '#E67E22',
  color: disabled ? '#666' : '#fff',
  border: 'none',
  borderRadius: '6px',
  fontWeight: 'bold',
  fontSize: '0.95rem',
  cursor: disabled ? 'not-allowed' : 'pointer',
  transition: 'background-color 0.2s',
});

const UserProfilePage = ({ userId }) => {
  const [record, setRecord] = useState(null);

  const [nameInput, setNameInput] = useState('');
  const [nameMsg, setNameMsg] = useState({ text: '', error: false });

  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwMsg, setPwMsg] = useState({ text: '', error: false });

  useEffect(() => {
    const r = getUserRecord(userId);
    setRecord(r);
    if (r) setNameInput(r.username || '');
  }, [userId]);

  if (!record) {
    return (
      <div style={{ padding: '3rem', color: '#aaa', textAlign: 'center' }}>
        Profile not found.
      </div>
    );
  }

  const initials = (record.username || userId)
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() || '')
    .join('');

  const ratingCount = Object.keys(record.ratings || {}).length;

  const handleSaveName = () => {
    const result = updateDisplayName(userId, nameInput);
    if (result.success) {
      setRecord((prev) => ({ ...prev, username: nameInput.trim() }));
      setNameMsg({ text: 'Display name updated.', error: false });
    } else {
      setNameMsg({ text: result.error, error: true });
    }
  };

  const handleSavePassword = () => {
    if (newPw !== confirmPw) {
      setPwMsg({ text: 'New passwords do not match.', error: true });
      return;
    }
    const result = updatePassword(userId, currentPw, newPw);
    if (result.success) {
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
      setPwMsg({ text: 'Password changed successfully.', error: false });
    } else {
      setPwMsg({ text: result.error, error: true });
    }
  };

  return (
    <div style={{ maxWidth: '560px', margin: '0 auto', padding: '2rem 1rem' }}>

      {/* Avatar + identity header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', marginBottom: '2rem' }}>
        <div style={{
          width: '72px', height: '72px', borderRadius: '50%',
          backgroundColor: '#E67E22',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '1.6rem', fontWeight: 'bold', color: '#fff', flexShrink: 0,
        }}>
          {initials || '?'}
        </div>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', color: '#fff' }}>
            {record.username || userId}
          </h2>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.9rem', color: '#888' }}>
            {userId}
          </p>
        </div>
      </div>

      {/* Stats */}
      <Section title="Stats">
        <div style={{ display: 'flex', gap: '2rem' }}>
          <div>
            <p style={{ margin: 0, fontSize: '1.8rem', fontWeight: 'bold', color: '#E67E22' }}>
              {ratingCount}
            </p>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.82rem', color: '#aaa' }}>
              beers rated
            </p>
          </div>
          <div>
            <p style={{ margin: 0, fontSize: '1.8rem', fontWeight: 'bold', color: record.coldStartCompleted ? '#2ecc71' : '#e74c3c' }}>
              {record.coldStartCompleted ? '✓' : '✗'}
            </p>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.82rem', color: '#aaa' }}>
              taste profile
            </p>
          </div>
        </div>
      </Section>

      {/* Edit display name */}
      <Section title="Display Name">
        <input
          style={inputStyle}
          value={nameInput}
          onChange={(e) => { setNameInput(e.target.value); setNameMsg({ text: '', error: false }); }}
          maxLength={40}
          placeholder="Your display name"
        />
        <Feedback msg={nameMsg.text} isError={nameMsg.error} />
        <button
          style={btnStyle(!nameInput.trim() || nameInput.trim() === record.username)}
          disabled={!nameInput.trim() || nameInput.trim() === record.username}
          onClick={handleSaveName}
        >
          Save
        </button>
      </Section>

      {/* Change password */}
      <Section title="Change Password">
        {[
          { label: 'Current password', value: currentPw, setter: setCurrentPw },
          { label: 'New password',     value: newPw,     setter: setNewPw },
          { label: 'Confirm new password', value: confirmPw, setter: setConfirmPw },
        ].map(({ label, value, setter }) => (
          <div key={label} style={{ marginBottom: '0.75rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', color: '#aaa', marginBottom: '0.3rem' }}>
              {label}
            </label>
            <input
              type="password"
              style={inputStyle}
              value={value}
              onChange={(e) => { setter(e.target.value); setPwMsg({ text: '', error: false }); }}
            />
          </div>
        ))}
        <Feedback msg={pwMsg.text} isError={pwMsg.error} />
        <button
          style={btnStyle(!currentPw || !newPw || !confirmPw)}
          disabled={!currentPw || !newPw || !confirmPw}
          onClick={handleSavePassword}
        >
          Change Password
        </button>
      </Section>

    </div>
  );
};

export default UserProfilePage;
