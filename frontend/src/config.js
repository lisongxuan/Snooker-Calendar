export default {
  backendUrl: import.meta.env.VITE_BACKEND_URL || "https://snookerapis.arkady14.fun",
  defaultLanguage: import.meta.env.VITE_DEFAULT_LANGUAGE || "en",
  umamiScriptSrc: import.meta.env.VITE_UMAMI_SCRIPT_SRC || "",
  umamiScriptdata: import.meta.env.VITE_UMAMI_SCRIPT_DATA || "",
  timezone: import.meta.env.VITE_TIMEZONE || 'Asia/Shanghai'
};
