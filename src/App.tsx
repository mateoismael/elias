import { useEffect, useState } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { LandingPage } from './components/LandingPage';
import { Dashboard } from './components/Dashboard';
import { UnsubscribePage } from './components/UnsubscribePage';

// ✅ SOLUCIÓN: Usar variable de entorno en lugar de hardcodear
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// 🔒 VALIDACIÓN: Verificar que las variables de entorno estén configuradas
if (!GOOGLE_CLIENT_ID) {
  console.error('❌ VITE_GOOGLE_CLIENT_ID no está configurado');
  throw new Error('Configuración de Google OAuth faltante');
}

if (!import.meta.env.VITE_API_BASE_URL) {
  console.error('❌ VITE_API_BASE_URL no está configurado');
  throw new Error('Configuración de API faltante');
}

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