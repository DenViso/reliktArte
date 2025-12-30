export const generateUrl = (targetUrl: string) => {
  // Беремо бекенд з env і змінюємо http на https
  const BACKEND =
    process.env.REACT_APP_BACKEND_LINK?.replace(/^http:\/\//, "https://") ??
    "https://reliktarte-production.up.railway.app";

  const part = "api/v1";

  const isDomainNotEndsWithSlash = !BACKEND.endsWith("/");

  const validPart = `${isDomainNotEndsWithSlash ? "/" : ""}${
    !targetUrl.includes(part) ? part : ""
  }${!targetUrl.startsWith("/") ? "/" : ""}`;

  const secondPart = `${validPart}${targetUrl}`.replaceAll("//", "/");

  const url = `${BACKEND}${secondPart}`;

  console.log("🔍 ALL ENV:", process.env);
  console.log("🔍 BACKEND_LINK:", process.env.REACT_APP_BACKEND_LINK);

  return url;
};