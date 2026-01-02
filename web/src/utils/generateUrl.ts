export const generateUrl = (targetUrl: string): string => {
  if (!targetUrl) return "";

  // Базовий URL Railway бекенду
  const BASE_URL = process.env.REACT_APP_API_URL || "https://reliktarte-production.up.railway.app";
  
  // Очищуємо базу від слешів у кінці
  const cleanBase = BASE_URL.replace(/\/+$/, "");

  // Нормалізуємо шлях - додаємо "/" на початку якщо немає
  let path = targetUrl.startsWith("/") ? targetUrl : `/${targetUrl}`;

  // ОБРОБКА СТАТИЧНИХ ФАЙЛІВ (зображення, css, js)
  if (path.includes("/static/")) {
    // Видаляємо /api/v1 якщо випадково там опинилося
    const staticPath = path.replace("/api/v1", "");
    // Повертаємо повний URL до статичного файлу
    return `${cleanBase}${staticPath}`.replace(/([^:]\/)\/+/g, "$1");
  }

  // ОБРОБКА API ЗАПИТІВ
  const API_PREFIX = "/api/v1";
  
  // Додаємо /api/v1 якщо немає
  if (!path.includes(API_PREFIX)) {
    path = `${API_PREFIX}${path}`;
  }

  // Збираємо фінальний URL
  let fullUrl = `${cleanBase}${path}`;
  
  // Нормалізуємо подвійні слеші (крім https://)
  fullUrl = fullUrl.replace(/([^:]\/)\/+/g, "$1");
  
  // Додаємо слеш у кінець для API запитів (уникаємо 307 redirect)
  if (!fullUrl.endsWith("/")) {
    fullUrl += "/";
  }

  return fullUrl;
};