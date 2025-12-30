import axios from "axios";
import { generateUrl } from "./generateUrl";

export const getItems = async (url_part: string, params?: any) => {
  let validUrl = generateUrl(url_part);

  // Форсуємо HTTPS навіть для localhost
  validUrl = validUrl.replace(/^http:\/\//, "https://");

  // Для локального dev можна залишити http, якщо сервер не підтримує HTTPS
  if (window.location.hostname === "localhost" && !validUrl.startsWith("https://localhost")) {
    validUrl = validUrl.replace(/^https:\/\//, "http://");
  }

  // Додаємо query params
  if (params) {
    const query = new URLSearchParams(params).toString();
    if (query) {
      validUrl += `?${query}`;
    }
  }

  try {
    const response = await axios.get(validUrl);
    return response.data;
  } catch (error) {
    console.error("❌ getItems error:", error);
    throw error;
  }
};
