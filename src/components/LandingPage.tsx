import { useEffect } from 'react';
import { GoogleSignIn } from './landing/GoogleSignIn';

export function LandingPage() {
  // Check if user is already authenticated
  useEffect(() => {
    // Don't redirect if we're on unsubscribe page
    if (window.location.pathname === '/unsubscribe') {
      return;
    }
    
    const userData = localStorage.getItem('pseudosapiens_user');
    if (userData) {
      try {
        const user = JSON.parse(userData);
        if (user.email) {
          window.history.pushState({}, '', '/dashboard');
          window.dispatchEvent(new PopStateEvent('popstate'));
        }
      } catch (e) {
        localStorage.removeItem('pseudosapiens_user');
      }
    }
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Hero Section - Above the fold optimization */}
      <main className="px-4 py-16 sm:py-24">
        <div className="max-w-4xl mx-auto text-center">

          {/* Value Proposition - Clear and compelling */}
          <div className="mb-16">
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-gray-900 mb-6 leading-tight">
              Transforma tu día con
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"> frases únicas</span>
            </h1>

            <p className="text-xl sm:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed">
              Recibe frases motivacionales seleccionadas por IA que inspiran a miles de profesionales cada día
            </p>
          </div>

          {/* Social Proof - Strategic placement */}
          <div className="mb-12">
            <div className="flex flex-col sm:flex-row items-center justify-center gap-8 text-center">
              <div className="flex items-center gap-4">
                <div className="flex -space-x-2">
                  <div className="w-10 h-10 rounded-full bg-blue-500 border-2 border-white"></div>
                  <div className="w-10 h-10 rounded-full bg-green-500 border-2 border-white"></div>
                  <div className="w-10 h-10 rounded-full bg-purple-500 border-2 border-white"></div>
                  <div className="w-10 h-10 rounded-full bg-orange-500 border-2 border-white"></div>
                </div>
                <div className="text-left">
                  <div className="font-bold text-gray-900">1,250+</div>
                  <div className="text-sm text-gray-600">personas suscritas</div>
                </div>
              </div>

              <div className="text-center">
                <div className="font-bold text-gray-900">89,500</div>
                <div className="text-sm text-gray-600">frases enviadas</div>
              </div>
            </div>
          </div>

          {/* Primary CTA - Single focus */}
          <div className="mb-12">
            <GoogleSignIn />
            <p className="text-sm text-gray-500 mt-4">
              ✓ Gratis para siempre • ✓ Sin spam • ✓ Cancela cuando quieras
            </p>
          </div>

          {/* Value Props - Minimal and clear */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🎯</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Personalizada con IA</h3>
              <p className="text-gray-600 text-sm">Frases únicas generadas específicamente para ti</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">⚡</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">3 por semana</h3>
              <p className="text-gray-600 text-sm">Lunes, miércoles y viernes a las 8:00 AM</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🚀</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Dashboard personal</h3>
              <p className="text-gray-600 text-sm">Gestiona tus preferencias fácilmente</p>
            </div>
          </div>

          {/* Testimonial - Social proof */}
          <div className="mt-16 max-w-2xl mx-auto">
            <blockquote className="text-lg text-gray-700 italic mb-4">
              "Las frases de Steve Jobs me dieron la confianza para emprender.
              Ahora dirijo mi propia startup."
            </blockquote>
            <cite className="text-gray-600 font-medium">
              — Carlos Mendoza, CEO Tech Startup
            </cite>
          </div>

        </div>
      </main>
    </div>
  );
}