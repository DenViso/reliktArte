export const generateUrl = (targetUrl: string) => {
  const part = "api/v1";

  const isDomainNotEndsWithSlash = !(
    process.env.REACT_APP_BACKEND_LINK || "https://reliktarte-production.up.railway.app"
  ).endsWith("/");
  const validPart = `${isDomainNotEndsWithSlash ? "/" : ""}${
    !targetUrl.includes(part) ? part : ""
  }${!targetUrl.startsWith("/") ? "/" : ""}`;

  const secondPart = `${validPart}${targetUrl}`.replaceAll("//", "/");
  const url = `${
    process.env.REACT_APP_BACKEND_LINK || "https://reliktarte-production.up.railway.app"
  }${secondPart}`;
console.log("🔍 ALL ENV:", process.env);
console.log("🔍 BACKEND_LINK:", process.env.REACT_APP_BACKEND_LINK);
  return url;
};