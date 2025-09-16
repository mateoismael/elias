import { useState, useEffect } from "react";

type Step = "confirm" | "processing" | "success" | "error";

export function UnsubscribePage() {
  const [currentStep, setCurrentStep] = useState<Step>("confirm");
  const [email, setEmail] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [currentEmail, setCurrentEmail] = useState("");

  useEffect(() => {
    // Pre-fill email if provided in URL
    const urlParams = new URLSearchParams(window.location.search);
    const emailParam = urlParams.get("email");
    if (emailParam) {
      setEmail(emailParam);
    }
  }, []);

  useEffect(() => {
    // Auto-redirect after successful unsubscription
    if (currentStep === "success") {
      const timer = setTimeout(() => {
        goHome();
      }, 4000); // 4 seconds delay

      return () => clearTimeout(timer);
    }
  }, [currentStep]);

  const handleUnsubscribe = async () => {
    if (!email || !email.includes("@")) {
      setErrorMessage("Por favor, ingresa un correo electrónico válido.");
      return;
    }

    setCurrentEmail(email);
    setCurrentStep("processing");

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/webhook/unsubscribe`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email: email.toLowerCase() }),
        }
      );

      if (response.ok) {
        // Clear user session since they're no longer subscribed
        localStorage.removeItem("pseudosapiens_user");
        setCurrentStep("success");
      } else {
        throw new Error("Error en la desuscripción");
      }
    } catch (error) {
      console.error("Unsubscribe error:", error);
      setErrorMessage(
        "No pudimos procesar tu desuscripción. Por favor, inténtalo nuevamente."
      );
      setCurrentStep("error");
    }
  };

  const goToPreferences = () => {
    if (email) {
      // Try to redirect to dashboard if user wants to change preferences instead
      window.history.pushState({}, "", "/dashboard");
      window.dispatchEvent(new PopStateEvent("popstate"));
    } else {
      window.history.pushState({}, "", "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  };

  const goHome = () => {
    window.history.pushState({}, "", "/");
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const retryUnsubscribe = () => {
    setEmail(currentEmail);
    setCurrentStep("confirm");
    setErrorMessage("");
  };

  const renderStep = () => {
    switch (currentStep) {
      case "confirm":
        return (
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">
              ¿Deseas desuscribirte?
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mb-6">
              Lamentamos que te vayas. Ingresa tu correo electrónico para
              confirmar tu desuscripción.
            </p>

            <div className="mb-6">
              <label
                htmlFor="email-input"
                className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 text-left"
              >
                Correo electrónico:
              </label>
              <input
                type="email"
                id="email-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@email.com"
                required
                autoComplete="email"
                className="w-full px-4 py-3 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-slate-700 dark:text-white"
                onKeyDown={(e) => e.key === "Enter" && handleUnsubscribe()}
              />
            </div>

            {errorMessage && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-600 dark:text-red-400 text-sm">
                  {errorMessage}
                </p>
              </div>
            )}

            <div className="space-y-3">
              <button
                onClick={handleUnsubscribe}
                className="w-full bg-red-600 hover:bg-red-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
              >
                Desuscribirme definitivamente
              </button>

              <button
                onClick={goToPreferences}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
              >
                Mejor cambiar frecuencia
              </button>

              <button
                onClick={goHome}
                className="w-full bg-transparent hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 py-3 px-4 rounded-lg font-medium border border-slate-300 dark:border-slate-600 transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        );

      case "processing":
        return (
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">
              Procesando...
            </h1>
            <div className="py-8">
              <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto"></div>
            </div>
            <p className="text-slate-600 dark:text-slate-400">
              Estamos procesando tu solicitud de desuscripción.
            </p>
          </div>
        );

      case "success":
        return (
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="text-green-600 dark:text-green-400 text-2xl">
                ✓
              </span>
            </div>

            <h1 className="text-2xl font-bold text-green-600 dark:text-green-400 mb-4">
              Desuscripción Completada
            </h1>

            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-6">
              <p className="text-green-800 dark:text-green-200">
                <strong>Tu suscripción ha sido cancelada exitosamente.</strong>
              </p>
              <p className="text-green-700 dark:text-green-300 mt-2">
                Ya no recibirás más frases motivacionales en tu correo
                electrónico. Si cambiaste de opinión, siempre puedes volver a
                suscribirte en nuestro sitio web.
              </p>
            </div>

            <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4 mb-6">
              <p className="text-slate-600 dark:text-slate-400 text-sm">
                <strong>¿Te despides por ahora?</strong>
                <br />
                Esperamos verte pronto de nuevo. Siempre estaremos aquí para
                inspirarte cuando lo necesites.
              </p>
            </div>

            <div className="text-slate-500 dark:text-slate-400 text-sm">
              Serás redirigido al inicio en unos segundos...
            </div>
          </div>
        );

      case "error":
        return (
          <div className="text-center">
            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="text-red-600 dark:text-red-400 text-2xl">✕</span>
            </div>

            <h1 className="text-2xl font-bold text-red-600 dark:text-red-400 mb-4">
              Hubo un problema
            </h1>

            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
              <p className="text-red-800 dark:text-red-200">{errorMessage}</p>
            </div>

            <div className="space-y-3">
              <button
                onClick={retryUnsubscribe}
                className="w-full bg-red-600 hover:bg-red-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
              >
                Intentar nuevamente
              </button>

              <button
                onClick={goHome}
                className="w-full bg-transparent hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 py-3 px-4 rounded-lg font-medium border border-slate-300 dark:border-slate-600 transition-colors"
              >
                Volver al inicio
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 p-8">
        {renderStep()}
      </div>
    </div>
  );
}
