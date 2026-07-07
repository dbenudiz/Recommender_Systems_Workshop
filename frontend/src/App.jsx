import { useState } from 'react';
import AuthScreen from './components/AuthScreen';
import RecommenderDashboard from './components/Dashboard';
import LandingPage from './components/LandingPage';
import './components/Dashboard.css';
import { saveColdStartRatings } from './services/authService';
import ColdStartRouter from './components/ColdStartRouter';
import StavAssistant from './components/StavAssistant'; 

// TEMP DEMO: jump straight to a real trained user (verified in
// data/train_set.csv / artifacts/cf_user_ids.npy), skipping AuthScreen
// registration entirely.
const DEMO_TRAINED_USER = {
  email: 'demo@rubeer.dev',
  userId: 'Ungstrup', // exact case must match cf.user_id_to_index key
  username: 'Ungstrup (demo)',
  needsColdStart: false,
  ratings: {},
};

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [needsColdStart, setNeedsColdStart] = useState(false);
  const [coldStartRecs, setColdStartRecs] = useState(null);
  const [isNewUser, setIsNewUser] = useState(false);
  const isLoggedIn = currentUser !== null;
  const [showAuth, setShowAuth] = useState(false);
  const [initialAuthView, setInitialAuthView] = useState(true); 

  const handleColdStartComplete = async ({ recs, ratedBeers }) => {
    if (currentUser.email) {
      saveColdStartRatings(currentUser.email, ratedBeers || {});
    }
    if (recs) {
      setColdStartRecs(recs);
    }
    setNeedsColdStart(false);
    setIsNewUser(true);  
  };

  const handleLogin = (userData, requiresColdStart) => {
    setCurrentUser(userData);
    setNeedsColdStart(requiresColdStart);
    setShowAuth(false); 
  };

  const handleLogout = () => {
    setCurrentUser(null);
  };

  const handleStartAuth = (isLogin) => {
    setInitialAuthView(isLogin);
    setShowAuth(true);
  };

  // TEMP DEMO: jump straight to the trained demo user.
  const handleDemoLogin = () => {
    setColdStartRecs(null);
    setIsNewUser(false);
    handleLogin(DEMO_TRAINED_USER, false);
  };

  const renderCurrentScreen = () => {
    if (!currentUser && showAuth) {
      return (
        <AuthScreen 
          onLogin={handleLogin} 
          initialIsLogin={initialAuthView}
          onBack={() => setShowAuth(false)} 
        />
      );
    }

    if (!currentUser && !showAuth) {
      return <LandingPage onStartAuth={handleStartAuth} />;
    }

    if (needsColdStart) {
      return (
        <ColdStartRouter
          currentUser={currentUser}
          onComplete={handleColdStartComplete}
        />
      );
    }

    return (
      <RecommenderDashboard
        coldStartRecs={coldStartRecs}
        userId={currentUser.userId}
        onLogout={handleLogout}
        isNewUser={isNewUser}
        onNewUserDismiss={() => setIsNewUser(false)}
      />
    );
  };

  return (
    <>
      {renderCurrentScreen()}
      {isLoggedIn && <StavAssistant />}
      {/* TEMP DEMO: quick-switch button, remove before shipping */}
      {!currentUser && (
      <div style={{ position: 'fixed', bottom: 12, left: 12, zIndex: 9999 }}>
        <button
          onClick={handleDemoLogin}
          style={{
            backgroundColor: '#E67E22',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            padding: '0.6rem 1rem',
            fontWeight: 'bold',
            fontSize: '0.9rem',
            cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.5)',
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#d67118'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#E67E22'; }}
        >
          Demo: Trained User
        </button>
      </div>
      )}
    </>
  );
}

export default App;