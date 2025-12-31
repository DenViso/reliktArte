export const generateUrl = (targetUrl: string): string => {
  const base = process.env.REACT_APP_BACKEND_LINK ;
  // || "https://reliktarte-production.up.railway.app"
  const isLocal = window.location.hostname === "localhost";
  let finalBase = base.replace(/\/+$/, "");
  
  if (isLocal) finalBase = finalBase.replace(/^https:\/\//, "http://");
  else finalBase = finalBase.replace(/^http:\/\//, "https://");

  // Якщо шлях містить картинку, НЕ додаємо api/v1
  if (targetUrl.includes("static/")) {
    const cleanPath = targetUrl.startsWith("/") ? targetUrl : `/${targetUrl}`;
    return `${finalBase}${cleanPath}`;
  }

  // Для API запитів
  const API_PART = "api/v1";
  let path = targetUrl.startsWith("/") ? targetUrl : `/${targetUrl}`;
  if (!path.includes(API_PART)) path = `/${API_PART}${path}`;

  return `${finalBase}${path}`.replace(/\/+/g, "/").replace(":/", "://");
};