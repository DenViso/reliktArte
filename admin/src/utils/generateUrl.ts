export const generateUrl = (targetUrl: string) => {
    const part = "api/v1";

    // Беремо бекенд із змінної оточення або дефолтний HTTPS
    let backend = process.env.REACT_APP_BACKEND_LINK || "https://reliktarte-production.up.railway.app";

    // Примусово HTTPS
    if (!backend.startsWith("https://")) {
        backend = backend.replace(/^http:\/\//, "https://");
    }

    // Прибираємо зайві слеші в кінці бекенду
    backend = backend.replace(/\/+$/, "");

    // Формуємо правильний шлях
    const pathPrefix = !targetUrl.includes(part) ? `/${part}` : "";
    const path = `${pathPrefix}/${targetUrl}`.replace(/\/+/g, "/");

    // Об’єднуємо backend і path без подвійних слешів після домену
    const url = `${backend}${path}`.replace(/([^:]\/)\/+/g, "$1");

    return url;
};
