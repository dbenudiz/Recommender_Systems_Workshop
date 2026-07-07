import { useState } from 'react';
import AuthScreen from './components/AuthScreen';
import RecommenderDashboard from './components/Dashboard';
import LandingPage from './components/LandingPage';
import './components/Dashboard.css';
import { saveColdStartRatings } from './services/authService';
import ColdStartRouter from './components/ColdStartRouter';
import StavAssistant from './components/StavAssistant'; 

// TEMP DEMO: quick-switch users for live demoing trained vs. cold-start
// behavior without re-registering through AuthScreen each time.
const DEMO_TRAINED_USER = {
  email: 'demo@rubeer.dev',
  userId: 'Ungstrup', // exact case must match cf.user_id_to_index key
  username: 'Ungstrup (demo)',
  needsColdStart: false,
  ratings: {},
};

const DEMO_COLD_START_USER = {
  email: 'demo-cold@rubeer.dev',
  userId: 'demo-cold@rubeer.dev',
  username: 'New Demo User',
  needsColdStart: true,
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

  // TEMP DEMO: jump straight to a trained or cold-start user, skipping
  // AuthScreen/registration entirely.
  const handleDemoSwitch = (demoUser) => {
    setColdStartRecs(null);
    setIsNewUser(false);
    handleLogin(demoUser, demoUser.needsColdStart);
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
      {/* TEMP DEMO: quick-switch panel, remove before shipping */}
      <div
        style={{
          position: 'fixed',
          bottom: 12,
          right: 12,
          zIndex: 9999,
          display: 'flex',
          gap: 8,
        }}
      >
        <button onClick={() => handleDemoSwitch(DEMO_TRAINED_USER)}>
          Demo: Trained User
        </button>
        <button onClick={() => handleDemoSwitch(DEMO_COLD_START_USER)}>
          Demo: Cold Start
        </button>
      </div>
    </>
  );
}

export default App;