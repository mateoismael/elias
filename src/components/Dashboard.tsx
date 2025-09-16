import { useState, useEffect } from "react";

interface UserData {
  id: string;
  email: string;
  name: string;
  auth_method: string;
  avatar_url?: string;
}

export function Dashboard() {
  const [user, setUser] = useState<UserData | null>(null);
  const [phrasesCount, setPhrasesCount] = useState(0);
  const [currentPlan, setCurrentPlan] = useState("weekly-3");
  const [isChangingPlan, setIsChangingPlan] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState<string | null>(null);
  const [showUnsubscribe, setShowUnsubscribe] = useState(false);
  const [isUnsubscribing, setIsUnsubscribing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const loadUserData = async (email: string) => {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/webhook/user-data`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }),
        }
      );

      const data = await response.json();

      if (response.ok && data.status === "success") {
        setCurrentPlan(data.user.current_plan);
        setPhrasesCount(data.user.phrases_count);
      } else {
        console.warn("Could not load user data:", data.message);
        // Mantener valores por defecto
      }
    } catch (error) {
      console.warn("Error loading user data:", error);
      // Mantener valores por defecto
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Load user data
    const userData = localStorage.getItem("pseudosapiens_user");
    if (userData) {
      const parsedUser = JSON.parse(userData);
      setUser(parsedUser);
      // Cargar datos reales del servidor
      loadUserData(parsedUser.email);
    } else {
      // Redirect to landing if no user data
      window.history.pushState({}, "", "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("pseudosapiens_user");
    window.history.pushState({}, "", "/");
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const handlePlanChange = async (newPlan: string) => {
    if (newPlan === currentPlan || !user?.email) return;

    setIsChangingPlan(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/webhook/update-plan`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: user.email,
            frequency: newPlan,
          }),
        }
      );

      const data = await response.json();

      if (response.ok && data.status === "success") {
        setCurrentPlan(newPlan);
        setShowConfirmation(
          `Plan actualizado a ${
            newPlan === "1-daily" ? "Frecuencia 1" : "Frecuencia 0"
          }`
        );
        setTimeout(() => setShowConfirmation(null), 3000);
      } else {
        throw new Error(data.message || "Error al actualizar plan");
      }
    } catch (error) {
      console.error("Error updating plan:", error);
      setShowConfirmation("Error al actualizar plan. Intenta de nuevo.");
      setTimeout(() => setShowConfirmation(null), 3000);
    } finally {
      setIsChangingPlan(false);
    }
  };

  const handleUnsubscribe = async () => {
    if (!user?.email) return;

    setIsUnsubscribing(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/webhook/unsubscribe`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email: user.email }),
        }
      );

      if (response.ok) {
        // Redirect to unsubscribe success page
        window.history.pushState({}, "", `/unsubscribe?email=${user.email}`);
        window.dispatchEvent(new PopStateEvent("popstate"));
      } else {
        throw new Error("Failed to unsubscribe");
      }
    } catch (error) {
      console.error("Unsubscribe error:", error);
      setShowConfirmation("Error al cancelar suscripción. Intenta de nuevo.");
      setTimeout(() => setShowConfirmation(null), 3000);
    } finally {
      setIsUnsubscribing(false);
      setShowUnsubscribe(false);
    }
  };

  if (!user || isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Cargando tu dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
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

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white mb-8">
          <h2 className="text-2xl font-bold mb-2">
            ¡Hola, {user.name.split(" ")[0]}! 👋
          </h2>
          <p className="text-indigo-100">
            Tu espacio personal de inspiración diaria
          </p>
        </div>

        {/* Phrases Counter */}
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm mb-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                Frases Enviadas
              </p>
              <p className="text-4xl font-bold text-slate-900 dark:text-white mt-2">
                {phrasesCount}
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Total recibidas hasta ahora
              </p>
            </div>
            <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center">
              <span className="text-blue-600 dark:text-blue-400 text-2xl">📧</span>
            </div>
          </div>
        </div>

        {/* Plan Selection */}
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm mb-8">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Configuración de Frecuencia
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            {/* Frequency 0 Plan */}
            <div
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                currentPlan === "weekly-3"
                  ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20"
                  : "border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500"
              }`}
              onClick={() => handlePlanChange("weekly-3")}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="text-base font-medium text-slate-900 dark:text-white">
                  Frecuencia 0
                </div>
                {currentPlan === "weekly-3" && (
                  <span className="text-indigo-600 dark:text-indigo-400 text-sm">
                    ✓ Activo
                  </span>
                )}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">
                3 frases por semana
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                Lunes, Miércoles, Viernes
              </div>
            </div>

            {/* Frequency 1 Plan */}
            <div
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                currentPlan === "1-daily"
                  ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20"
                  : "border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500"
              }`}
              onClick={() => handlePlanChange("1-daily")}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="text-base font-medium text-slate-900 dark:text-white">
                  Frecuencia 1
                </div>
                {currentPlan === "1-daily" && (
                  <span className="text-indigo-600 dark:text-indigo-400 text-sm">
                    ✓ Activo
                  </span>
                )}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">
                1 frase cada día
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                Todos los días a las 8:00 AM
              </div>
            </div>
          </div>
        </div>

        {/* Account Actions */}
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Gestión de Cuenta
          </h3>

          <button
            onClick={() => setShowUnsubscribe(true)}
            className="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 underline transition-colors"
          >
            Cancelar suscripción
          </button>
        </div>
      </main>

      {/* Confirmation Toast */}
      {showConfirmation && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50">
          <div className="flex items-center">
            <span className="mr-2">✓</span>
            {showConfirmation}
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {isChangingPlan && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-800 rounded-lg p-6 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <p className="text-slate-900 dark:text-white">Actualizando plan...</p>
          </div>
        </div>
      )}

      {/* Unsubscribe Confirmation Modal */}
      {showUnsubscribe && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
              ¿Cancelar suscripción?
            </h3>
            <p className="text-slate-600 dark:text-slate-400 mb-6">
              Lamentamos que te vayas. Al cancelar no recibirás más frases
              motivacionales en tu correo.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setShowUnsubscribe(false)}
                className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                disabled={isUnsubscribing}
              >
                Mantener suscripción
              </button>
              <button
                onClick={handleUnsubscribe}
                disabled={isUnsubscribing}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isUnsubscribing ? "Procesando..." : "Confirmar cancelación"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}