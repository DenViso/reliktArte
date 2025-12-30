export const generateUrl = (targetUrl: string) => {
    const part = "api/v1";

    // Беремо бекенд із змінної оточення або дефолтний HTTPS
    const backend = (process.env.REACT_APP_BACKEND_LINK || "https://reliktarte-production.up.railway.app")
        .replace(/^http:\/\//, "https://")  // примусово HTTPS
        .replace(/\/+$/, ""); // прибрати зайві слеші в кінці

    // Формуємо правильний шлях
    const pathPrefix = !targetUrl.includes(part) ? `/${part}` : "";
    const path = `${pathPrefix}/${targetUrl}`.replace(/\/+/g, "/"); // прибираємо подвійні слеші

    const url = `${backend}${path}`;
    return url;
};
