import { useEffect, useState } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { LandingPage } from './components/LandingPage';
import { Dashboard } from './components/Dashboard';
import { UnsubscribePage } from './components/UnsubscribePage';

const GOOGLE_CLIENT_ID = '970302400473-3umkhto0uhqs08p5njnhbm90in9lcp49.apps.googleusercontent.com';

function App() {
  const [currentPage, setCurrentPage] = useState<'landing' | 'dashboard' | 'unsubscribe'>('landing');

  useEffect(() => {
    // Simple routing based on URL path
    const path = window.location.pathname;
    if (path === '/dashboard') {
      setCurrentPage('dashboard');
    } else if (path === '/unsubscribe') {
      setCurrentPage('unsubscribe');
    } else {
      setCurrentPage('landing');
    }

    // Listen for navigation changes
    const handlePopState = () => {
      const newPath = window.location.pathname;
      if (newPath === '/dashboard') {
        setCurrentPage('dashboard');
      } else if (newPath === '/unsubscribe') {
        setCurrentPage('unsubscribe');
      } else {
        setCurrentPage('landing');
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Update browser URL without reload
  useEffect(() => {
    let expectedPath = '/';
    if (currentPage === 'dashboard') expectedPath = '/dashboard';
    else if (currentPage === 'unsubscribe') expectedPath = '/unsubscribe';

    if (window.location.pathname !== expectedPath) {
      window.history.pushState({}, '', expectedPath);
    }
  }, [currentPage]);

  if (currentPage === 'dashboard') {
    return <Dashboard />;
  }

  if (currentPage === 'unsubscribe') {
    return <UnsubscribePage />;
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <LandingPage />
    </GoogleOAuthProvider>
  );
}

export default App;