import axios from "axios";
import { generateUrl } from "./generateUrl";

export const getItems = async (url_part: string, params?: any) => {
  const validUrl = generateUrl(url_part);

  try {
    // Axios сам додасть params як ?page=1 тощо
    const response = await axios.get(validUrl, { params });
    return response.data;
  } catch (error) {
    console.error("❌ getItems error:", error);
    throw error;
  }
};