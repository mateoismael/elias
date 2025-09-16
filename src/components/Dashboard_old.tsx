import { useState, useEffect } from "react";

interface UserData {
  id: string;
  email: string;
  name: string;
  auth_method: string;
  avatar_url?: string;
}

interface DashboardStats {
  totalPhrases: number;
  currentPlan: string;
  frequency: string;
}

export function Dashboard() {
  const [user, setUser] = useState<UserData | null>(null);
  const [stats, setStats] = useState<DashboardStats>({
    totalPhrases: 0,
    currentPlan: "weekly-3",
    frequency: "3 por semana",
  });
  const [selectedPlan, setSelectedPlan] = useState("weekly-3");
  const [isChangingPlan, setIsChangingPlan] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState<string | null>(null);
  const [showUnsubscribe, setShowUnsubscribe] = useState(false);
  const [isUnsubscribing, setIsUnsubscribing] = useState(false);

  useEffect(() => {
    // Load user data
    const userData = localStorage.getItem('pseudosapiens_user');
    if (userData) {
      const parsedUser = JSON.parse(userData);
      setUser(parsedUser);

      // Check if it's a new user (show onboarding)
      const hasSeenOnboarding = localStorage.getItem('hasSeenOnboarding');
      if (!hasSeenOnboarding) {
        setShowOnboarding(true);
      }
    } else {
      // Redirect to landing if no user data
      window.history.pushState({}, '', '/');
      window.dispatchEvent(new PopStateEvent('popstate'));
    }

    // Simulate loading stats
    setTimeout(() => {
      setStats({
        totalPhrases: 47,
        currentPlan: 'Plan Gratis',
        frequency: '3 por semana'
      });
    }, 500);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('pseudosapiens_user');
    localStorage.removeItem('hasSeenOnboarding');
    window.history.pushState({}, '', '/');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const completeOnboarding = () => {
    setShowOnboarding(false);
    localStorage.setItem('hasSeenOnboarding', 'true');
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">P</span>
              </div>
              <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
                Pseudosapiens
              </h1>
            </div>

            {/* User Info */}
            <div className="flex items-center gap-4">
              <div className="hidden sm:block text-right">
                <p className="text-sm font-medium text-slate-900 dark:text-white">
                  {user.name}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {user.email}
                </p>
              </div>

              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt="Avatar"
                  className="w-10 h-10 rounded-full border-2 border-slate-200 dark:border-slate-600"
                />
              ) : (
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">
                    {user.name.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}

              <button
                onClick={handleLogout}
                className="text-sm text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white px-3 py-1 rounded-md border border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500 transition-colors"
              >
                Salir
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { id: 'overview', name: 'Resumen', icon: '📊' },
              { id: 'preferences', name: 'Preferencias', icon: '⚙️' },
              { id: 'billing', name: 'Facturación', icon: '💳' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 hover:border-slate-300 dark:hover:border-slate-600'
                }`}
              >
                <span>{tab.icon}</span>
                {tab.name}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Welcome Message */}
            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white">
              <h2 className="text-2xl font-bold mb-2">
                ¡Hola, {user.name.split(' ')[0]}! 👋
              </h2>
              <p className="text-indigo-100">
                Bienvenido a tu dashboard personal de frases motivacionales
              </p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Total Phrases */}
              <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                      Frases Recibidas
                    </p>
                    <p className="text-3xl font-bold text-slate-900 dark:text-white mt-2">
                      {stats.totalPhrases}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex items-center justify-center">
                    <span className="text-blue-600 dark:text-blue-400 text-xl">📧</span>
                  </div>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-4">
                  +3 esta semana
                </p>
              </div>

              {/* Current Plan */}
              <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                      Plan Actual
                    </p>
                    <p className="text-xl font-bold text-slate-900 dark:text-white mt-2">
                      {stats.currentPlan}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-green-100 dark:bg-green-900/20 rounded-lg flex items-center justify-center">
                    <span className="text-green-600 dark:text-green-400 text-xl">✨</span>
                  </div>
                </div>
                <button className="text-xs text-indigo-600 dark:text-indigo-400 mt-4 hover:underline">
                  Mejorar plan
                </button>
              </div>

              {/* Frequency */}
              <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                      Frecuencia
                    </p>
                    <p className="text-xl font-bold text-slate-900 dark:text-white mt-2">
                      {stats.frequency}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/20 rounded-lg flex items-center justify-center">
                    <span className="text-purple-600 dark:text-purple-400 text-xl">⚡</span>
                  </div>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-4">
                  Lun, Mié, Vie
                </p>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                Última Frase Recibida
              </h3>
              <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4 border-l-4 border-indigo-500">
                <blockquote className="text-slate-700 dark:text-slate-300 italic mb-2">
                  "El éxito no es la clave de la felicidad. La felicidad es la clave del éxito."
                </blockquote>
                <cite className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                  — Albert Schweitzer
                </cite>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                  Recibida hace 2 días
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'preferences' && (
          <PreferencesTab 
            user={user} 
            stats={stats} 
            onPlanChange={(newPlan) => {
              setStats(prev => ({ ...prev, currentPlan: newPlan }));
            }}
          />
        )}

        {activeTab === 'billing' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                💳 Gestión de Facturación
              </h3>
              <p className="text-slate-600 dark:text-slate-400">
                Actualmente estás en el plan gratuito. ¡Disfruta de 3 frases motivacionales por semana!
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Onboarding Modal */}
      {showOnboarding && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 max-w-md w-full text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="text-white text-2xl">🎉</span>
            </div>

            <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">
              ¡Bienvenido a Pseudosapiens!
            </h2>

            <p className="text-slate-600 dark:text-slate-400 mb-6">
              Tu viaje de inspiración diaria comienza ahora. Recibirás frases motivacionales
              cuidadosamente seleccionadas 3 veces por semana.
            </p>

            <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4 mb-6 text-left">
              <p className="text-sm text-slate-600 dark:text-slate-400 italic">
                "El viaje de mil millas comienza con un solo paso."
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-500 mt-2 font-medium">
                — Lao Tzu
              </p>
            </div>

            <button
              onClick={completeOnboarding}
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white py-3 px-6 rounded-lg font-medium hover:from-indigo-600 hover:to-purple-700 transition-all"
            >
              ¡Comenzar mi viaje! 🚀
            </button>
          </div>
        </div>
      )}
    </div>
  );
}