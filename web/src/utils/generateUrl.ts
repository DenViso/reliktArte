export const generateUrl = (targetUrl: string): string => {
   console.log("🔍 ENV CHECK:", {
    REACT_APP_API_URL: process.env.REACT_APP_API_URL,
    NODE_ENV: process.env.NODE_ENV,
  });
  
  if (!targetUrl) return "";

  // HARDCODED для продакшену
  const BASE_URL = "https://reliktarte-production.up.railway.app";
  const cleanBase = BASE_URL.replace(/\/+$/, "");

  // Якщо вже повний URL - повертаємо як є
  if (targetUrl.startsWith("http")) {
    return targetUrl;
  }

  let path = targetUrl.startsWith("/") ? targetUrl : `/${targetUrl}`;

  // ОБРОБКА СТАТИЧНИХ ФАЙЛІВ
  if (path.includes("/static/") || path.startsWith("/static")) {
    const staticPath = path.replace("/api/v1", "");
    return `${cleanBase}${staticPath}`.replace(/([^:]\/)\/+/g, "$1");
  }

  // ОБРОБКА API ЗАПИТІВ
  const API_PREFIX = "/api/v1";
  
  if (!path.includes(API_PREFIX)) {
    path = `${API_PREFIX}${path}`;
  }

  let fullUrl = `${cleanBase}${path}`.replace(/([^:]\/)\/+/g, "$1");

  // Додаємо слеш ПЕРЕД query параметрами
  if (fullUrl.includes("?")) {
    const [urlPath, queryString] = fullUrl.split("?");
    if (!urlPath.endsWith("/")) {
      fullUrl = `${urlPath}/?${queryString}`;
    }
  } else {
    if (!fullUrl.endsWith("/")) {
      fullUrl += "/";
    }
  }

  return fullUrl;
};