import { useEffect } from "react";
import { GoogleSignIn } from "./landing/GoogleSignIn";

export function LandingPage() {
  // Check if user is already authenticated
  useEffect(() => {
    // Don't redirect if we're on unsubscribe page
    if (window.location.pathname === "/unsubscribe") {
      return;
    }

    const userData = localStorage.getItem("pseudosapiens_user");
    if (userData) {
      try {
        const user = JSON.parse(userData);
        if (user.email) {
          window.history.pushState({}, "", "/dashboard");
          window.dispatchEvent(new PopStateEvent("popstate"));
        }
      } catch (e) {
        localStorage.removeItem("pseudosapiens_user");
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
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                {" "}
                frases únicas
              </span>
            </h1>

            <p className="text-xl sm:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed">
              Recibe reflexiones cuidadosamente seleccionadas de referentes en
              diversos campos profesionales
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
                  <div className="text-sm text-gray-600">
                    personas suscritas
                  </div>
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
              ✓ Frecuencias gratis • ✓ Sin spam • ✓ Cancela cuando quieras
            </p>
          </div>

          {/* Value Props - Minimal and clear */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🎯</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">
                Contenido curado
              </h3>
              <p className="text-gray-600 text-sm">
                Reflexiones de referentes profesionales
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">⚡</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">
                Envío inteligente
              </h3>
              <p className="text-gray-600 text-sm">
                Asuntos personalizados con tecnología IA
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🚀</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">
                Dashboard personal
              </h3>
              <p className="text-gray-600 text-sm">
                Gestiona tus preferencias fácilmente
              </p>
            </div>
          </div>

          {/* Testimonials - Social proof */}
          <div className="mt-16 max-w-4xl mx-auto">
            <h3 className="text-2xl font-bold text-gray-900 text-center mb-8">
              Lo que dicen nuestros suscriptores
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Testimonial 1 */}
              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
                <blockquote className="text-gray-700 mb-4">
                  "Honestamente no esperaba mucho, pero llegó una frase de Steve
                  Jobs justo cuando estaba dudando si seguir en mi trabajo actual.
                  Me hizo replantear todo."
                </blockquote>
                <div className="flex items-center">
                  <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white font-medium mr-3">
                    C
                  </div>
                  <cite className="text-gray-600 font-medium not-italic">
                    Carlos R., Analista financiero
                  </cite>
                </div>
              </div>

              {/* Testimonial 2 */}
              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
                <blockquote className="text-gray-700 mb-4">
                  "Una frase de Maya Angelou llegó justo cuando me sentía agobiada por todo. Me recordó que puedo cambiar mi actitud aunque no pueda cambiar la situación. Ese email me salvó la semana."
                </blockquote>
                <div className="flex items-center">
                  <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white font-medium mr-3">
                    A
                  </div>
                  <cite className="text-gray-600 font-medium not-italic">
                    Ana L., Coordinadora de proyectos
                  </cite>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
