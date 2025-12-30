// src/utils/getItems.ts
import axios from "axios";
import { generateUrl } from "./generateUrl";

export const getItems = async (url_part: string, params?: any) => {
  const validUrl = generateUrl(url_part);

  try {
    // Передаємо params другим аргументом в axios — він сам зробить ?page=1&limit=10
    const response = await axios.get(validUrl, { params });
    return response.data;
  } catch (error) {
    console.error("❌ getItems error:", error);
    throw error;
  }
};