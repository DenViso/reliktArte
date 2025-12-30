export const generateUrl = (targetUrl: string): string => {
  // 1. Пріоритет змінній з Vercel, якщо її немає — дефолт
  const base = process.env.REACT_APP_BACKEND_LINK || "https://reliktarte-production.up.railway.app";
  
  // 2. Визначаємо правильний протокол
  const isLocal = window.location.hostname === "localhost";
  
  // Якщо ми локально — використовуємо http, якщо на проді — СУВОРО https
  let finalBase = base;
  if (isLocal) {
    finalBase = base.replace(/^https:\/\//, "http://");
  } else {
    finalBase = base.replace(/^http:\/\//, "https://");
  }

  const API_PART = "api/v1";
  
  // 3. Формуємо шлях, уникаючи подвійних слешів
  let path = targetUrl.startsWith("/") ? targetUrl : `/${targetUrl}`;
  if (!path.includes(API_PART)) {
    path = `/${API_PART}${path}`;
  }

  const url = `${finalBase.replace(/\/+$/, "")}${path}`;
  
  console.log("🌍 Environment:", isLocal ? "Local" : "Production");
  console.log("🔗 Generated URL:", url);

  return url;
};