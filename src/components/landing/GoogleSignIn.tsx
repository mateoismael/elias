import { useState } from "react";
import { GoogleLogin } from "@react-oauth/google";

export function GoogleSignIn() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleSuccess = async (credentialResponse: any) => {
    console.log("Google Sign-In successful:", credentialResponse);
    setIsLoading(true);
    setError(null);

    try {
      const credential = credentialResponse.credential;

      if (!credential) {
        throw new Error("No credential received from Google");
      }

      // Send credential to webhook
      const apiResponse = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/webhook/google-signin`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            credential: credential,
            frequency: "weekly-3", // Default to free plan
          }),
        }
      );

      const data = await apiResponse.json();

      if (data.success) {
        // Save user data to localStorage for dashboard access
        const userData = {
          id: data.user.id,
          email: data.user.email,
          name: data.user.name,
          auth_method: data.user.auth_method,
          avatar_url: data.user.avatar_url || null,
        };
        localStorage.setItem("pseudosapiens_user", JSON.stringify(userData));

        // Redirect to dashboard
        setTimeout(() => {
          window.history.pushState({}, "", "/dashboard");
          window.dispatchEvent(new PopStateEvent("popstate"));
        }, 1500);
      } else {
        throw new Error(data.error || "Authentication failed");
      }
    } catch (error) {
      console.error("Google Sign-In error:", error);
      setError("Error al registrarse. Intenta de nuevo.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleError = () => {
    setError("Error al conectar con Google. Intenta de nuevo.");
  };

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <div className="text-red-600 font-medium mb-2">❌ {error}</div>
          <button
            onClick={() => {
              setError(null);
              window.location.reload();
            }}
            className="text-red-600 underline hover:no-underline text-sm"
          >
            Intentar de nuevo
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="inline-flex items-center gap-3 text-green-700 font-medium">
            <div className="w-5 h-5 border-2 border-current border-t-transparent animate-spin rounded-full" />
            <span>✨ Registrando tu cuenta...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Primary CTA Button */}
      <div className="flex justify-center">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-1">
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={handleGoogleError}
            size="large"
            shape="pill"
            text="continue_with"
            theme="filled_blue"
            width={320}
          />
        </div>
      </div>

      {/* Fallback in case Google button doesn't load */}
      <div className="text-center">
        <button
          onClick={() => window.location.reload()}
          className="text-sm text-gray-500 hover:text-gray-700 underline"
        >
          ¿No aparece el botón? Recarga la página
        </button>
      </div>
    </div>
  );
}
