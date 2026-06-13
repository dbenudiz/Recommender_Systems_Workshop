import React, { useState } from 'react';
import AuthScreen from './components/AuthScreen';
import RecommenderDashboard from './components/Dashboard';
import LandingPage from './components/LandingPage';
import CherryTartImage from './assets/Cherry Tart.jpg';
import citrusBlastImage from './assets/Citrus Blast.jpg';
import desertMirageImage from './assets/Sour Ale.jpg';
import galacticStoutImage from './assets/Galactic Stout.jpg';
import hazyHorizonImage from './assets/Hazy Horizon.jpg';
import midnightPorterImage from './assets/Midnight Porter.jpg';
import rubyRedImage from './assets/Ruby Red.jpg';
import crispMorningImage from './assets/Crisp Morning.jpg';
import goldenHourImage from './assets/Golden Hour.jpg';
import spicedPumpkinImage from './assets/Spiced Pumpkin.jpg';


// --- TEMPORARY COLD START PLACEHOLDER ---
const ColdStartQuestionnaire = ({ onComplete }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: '#141414', color: 'white' }}>
    <h2 style={{ color: '#E67E22' }}>Cold Start Questionnaire</h2>
    <p style={{ marginBottom: '2rem' }}>This is where the user will rate their first beers.</p>
    <button 
      onClick={onComplete} 
      style={{ padding: '0.8rem 1.5rem', background: '#E67E22', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: 'bold' }}
    >
      Simulate Completion
    </button>
  </div>
);

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [needsColdStart, setNeedsColdStart] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(true); 
  
  // NEW: State to control if the Auth Screen is visible
  const [showAuth, setShowAuth] = useState(false);
  const [initialAuthView, setInitialAuthView] = useState(true); // true = login, false = register

const dummyData = {
    swimlanes: [
      {
        id: 'top-matches',
        title: 'Top Matches for You',
        beers: [
          { id: 'b1', name: 'Galactic Stout', style: 'Imperial Stout', abv: 9.5, match_score: 0.98, rating: 4.8, image_url: galacticStoutImage },
          { id: 'b2', name: 'Hazy Horizon', style: 'NEIPA', abv: 6.8, match_score: 0.94, rating: 4.5, image_url: hazyHorizonImage },
          { id: 'b3', name: 'Crisp Morning', style: 'Pilsner', abv: 4.5, match_score: 0.91, rating: 4.2, image_url: crispMorningImage },
          { id: 'b4', name: 'Ruby Red', style: 'Amber Ale', abv: 5.5, match_score: 0.88, rating: 4.0, image_url: rubyRedImage }
        ]
      },
      {
        id: 'trending',
        title: 'Trending in Tel Aviv',
        beers: [
          { id: 'b5', name: 'Desert Mirage', style: 'Sour Ale', abv: 5.2, match_score: 0.85, rating: 4.1, image_url: desertMirageImage },
          { id: 'b6', name: 'Citrus Blast', style: 'IPA', abv: 7.2, match_score: 0.82, rating: 4.4, image_url: citrusBlastImage },
          { id: 'b7', name: 'Midnight Porter', style: 'Porter', abv: 6.0, match_score: 0.80, rating: 4.6, image_url: midnightPorterImage },
          { id: 'b8', name: 'Golden Hour', style: 'Wheat Beer', abv: 4.8, match_score: 0.77, rating: 3.9, image_url: goldenHourImage }
        ]
      },
      {
        id: 'try-something-new',
        title: 'Step Outside Your Comfort Zone',
        beers: [
          { id: 'b9', name: 'Spiced Pumpkin', style: 'Seasonal Ale', abv: 6.5, match_score: 0.65, rating: 3.8, image_url: spicedPumpkinImage },
          { id: 'b10', name: 'Cherry Tart', style: 'Fruited Sour', abv: 4.2, match_score: 0.58, rating: 4.3, image_url: CherryTartImage },
        ]
      }
    ]
  };

  const handleLogin = (userData, requiresColdStart) => {
    setCurrentUser(userData);
    setNeedsColdStart(requiresColdStart);
    setShowAuth(false); // Reset this so it's clean if they log out later
  };

  const handleLogout = () => {
    setCurrentUser(null);
  };

  const handleStartAuth = (isLogin) => {
    setInitialAuthView(isLogin);
    setShowAuth(true);
  };

  // 1. If not logged in AND Auth Screen is triggered, show Auth Screen
  if (!currentUser && showAuth) {
    return (
      <AuthScreen 
        onLogin={handleLogin} 
        isDemoMode={isDemoMode} 
        initialIsLogin={initialAuthView}
        onBack={() => setShowAuth(false)} // Gives them a way back to the landing page
      />
    );
  }

  // 2. If not logged in AND Auth Screen is NOT triggered, show Landing Page
  if (!currentUser && !showAuth) {
    return <LandingPage onStartAuth={handleStartAuth} />;
  }

  // 3. If logged in but needs cold start, show Questionnaire
  if (needsColdStart) {
    return <ColdStartQuestionnaire onComplete={() => setNeedsColdStart(false)} />;
  }

  // 4. Otherwise, show the main application
  return (
    <RecommenderDashboard 
      data={dummyData} 
      onLogout={handleLogout} 
    />
  );
}

export default App;