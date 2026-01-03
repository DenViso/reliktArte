// Стандартні розміри дверей
export const DEFAULT_DOOR_SIZES = [
  {
    id: 1,
    dimensions: "2000x600х40",
    width: 600,
    height: 2000,
  },
  {
    id: 2,
    dimensions: "2000x700х40",
    width: 700,
    height: 2000,
  },
  {
    id: 3,
    dimensions: "2000x800х40",
    width: 800,
    height: 2000,
  },
  {
    id: 4,
    dimensions: "2000x900х40",
    width: 900,
    height: 2000,
  },
  {
    id: 5,
    dimensions: "нестандартний",
    width: 0,
    height: 0,
  },
];

// Категорії, для яких використовуємо стандартні розміри
export const CATEGORIES_WITH_DEFAULT_SIZES = [1]; // ID категорії "Двері"