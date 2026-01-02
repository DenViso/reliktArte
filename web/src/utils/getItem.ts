import axios from 'axios';

export const getItem = async (url: string, params?: any) => {
  // Видаляємо зайві слеші
  const cleanUrl = url.replace(/\/+$/, '');
  
  // Перевірка на undefined в URL
  if (cleanUrl.includes('undefined')) {
    console.error('❌ Invalid URL with undefined:', cleanUrl);
    return null;
  }
  
  try {
    const response = await axios.get(cleanUrl, { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching item:', error);
    throw error;
  }
};