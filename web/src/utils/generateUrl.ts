export const generateUrl = (targetUrl: string): string => {
  console.log("🔍 ENV CHECK:", {
    REACT_APP_API_URL: process.env.REACT_APP_API_URL,
    NODE_ENV: process.env.NODE_ENV,
  });
  
  if (!targetUrl) return "";

  // ✅ В development використовуємо proxy (відносні шляхи)
  const isDevelopment = process.env.NODE_ENV === 'development';
  
  // Якщо вже повний URL - повертаємо як є
  if (targetUrl.startsWith("http")) {
    return targetUrl;
  }

  let path = targetUrl.startsWith("/") ? targetUrl : `/${targetUrl}`;

  // ОБРОБКА СТАТИЧНИХ ФАЙЛІВ
  if (path.includes("/static/") || path.startsWith("/static")) {
    const staticPath = path.replace("/api/v1", "");
    
    if (isDevelopment) {
      // В development - через proxy
      return staticPath.replace(/([^:]\/)\/+/g, "$1");
    }
    
    // В production - повний URL
    const BASE_URL = process.env.REACT_APP_API_URL || "https://reliktarte-production.up.railway.app";
    const cleanBase = BASE_URL.replace(/\/+$/, "");
    return `${cleanBase}${staticPath}`.replace(/([^:]\/)\/+/g, "$1");
  }

  // ОБРОБКА API ЗАПИТІВ
  const API_PREFIX = "/api/v1";
  
  if (!path.includes(API_PREFIX)) {
    path = `${API_PREFIX}${path}`;
  }

  // ✅ В development - повертаємо відносний шлях (proxy обробить)
  if (isDevelopment) {
    // Додаємо слеш ПЕРЕД query параметрами
    if (path.includes("?")) {
      const [urlPath, queryString] = path.split("?");
      if (!urlPath.endsWith("/")) {
        path = `${urlPath}/?${queryString}`;
      }
    } else {
      if (!path.endsWith("/")) {
        path += "/";
      }
    }
    return path;
  }

  // ✅ В production - повний URL
  const BASE_URL = process.env.REACT_APP_API_URL || "https://reliktarte-production.up.railway.app";
  const cleanBase = BASE_URL.replace(/\/+$/, "");
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