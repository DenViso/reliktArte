// src/utils/generateUrl.ts
export const generateUrl = (targetUrl: string): string => {
  // 1. Визначаємо базовий домен (без протоколу)
  const baseFromEnv = process.env.REACT_APP_BACKEND_LINK || "reliktarte-production.up.railway.app";
  const cleanBase = baseFromEnv.replace(/^https?:\/\//, "").replace(/\/+$/, "");

  // 2. Визначаємо протокол
  const isLocal = window.location.hostname === "localhost";
  const protocol = isLocal ? "http://" : "https://";

  // 3. Формуємо шлях API
  const API_PART = "api/v1";
  let path = targetUrl.startsWith("/") ? targetUrl : `/${targetUrl}`;
  if (!path.includes(API_PART)) {
    path = `/${API_PART}${path}`;
  }

  // 4. Склеюємо (URL конструктор сам прибере зайві слеші)
  return `${protocol}${cleanBase}${path}`;
};