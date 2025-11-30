export default {
  backend: import.meta.env.VITE_BACKEND || "snookerapis.arkady14.fun",
  backendUrl: import.meta.env.VITE_BACKEND_URL || "https://"+backend,
  backendWebCalUrl: import.meta.env.VITE_BACKEND_WEBCAL_URL || "webcal://"+backend,
  defaultLanguage: import.meta.env.VITE_DEFAULT_LANGUAGE || "en",
  umamiScriptSrc: import.meta.env.VITE_UMAMI_SCRIPT_SRC || "",
  umamiScriptdata: import.meta.env.VITE_UMAMI_SCRIPT_DATA || "",
  timezone: import.meta.env.VITE_TIMEZONE || Asia/Shanghai
};
