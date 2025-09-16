/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GOOGLE_CLIENT_ID: string;
  readonly VITE_API_BASE_URL: string;
  // Agregar más variables de entorno aquí según las necesites
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
