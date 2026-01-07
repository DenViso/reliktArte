import axios from "axios";
import { generateUrl } from "./generateUrl";

const accessTokenName = "ACCESS_RELIKTARTE_ADMIN_TOKEN";
const refreshTokenName = "REFRESH_RELIKTARTE_ADMIN_TOKEN";

export const getAccessToken = () => {
    return localStorage.getItem(accessTokenName);
};

export const getRefreshToken = () => {
    return localStorage.getItem(refreshTokenName);
};

export const setAccessToken = (token: string) => {
    return localStorage.setItem(accessTokenName, token);
};

export const setRefreshToken = (token: string) => {
    return localStorage.setItem(refreshTokenName, token);
};

export const validateToken = async () => {
    let isValid = false;

    const accessToken = getAccessToken();
    const refreshToken = getRefreshToken();

    if (accessToken) {
        const isTokenValid = await axios
            .post(generateUrl(
                // "api/v1/user/token/verify?as_admin=true"
                "api/v1/user/create/?as_admin=..."
            ), {
                token: accessToken,
            })
            .then((res) => res.data || false)
            .catch(() => false);
        isValid = isTokenValid;
    }

    if (!isValid && refreshToken) {
        const isRefreshTokenValid = await axios
            .post(
                generateUrl(
                    "api/v1/user/token/access_from_refresh?as_admin=true"
                ),
                {
                    token: refreshToken,
                }
            )
            .then((res) => {
                setAccessToken(res.data.access_token);
                setRefreshToken("");

                return true;
            })
            .catch(() => false);

        isValid = isRefreshTokenValid;
    }

    return isValid;
};

export const registerUser = async (data: any) => {
    return await axios
        .post(
            generateUrl(
                `api/v1/user/create?as_admin=${data.as_admin || false}`
            ),
            {
                ...data,
            }
        )
        .then(() => true)
        .catch((err) => ({
            error: err.response.data.detail || "Щось пішло не так.",
        }));
};

// export const singInAccount = async (data: any) => {
//     return await axios
//         .post(generateUrl("api/v1/user/auth?as_admin=true"), {
//             ...data,
//         })
//         .then((res) => {
//             setAccessToken(res.data.access_token);
//             setRefreshToken(res.data.refresh_token);

//             return true;
//         })
//         .catch((err) => ({
//             error: err.response.data.detail || "Щось пішло не так.",
//         }));
// };
export const singInAccount = async (data: any) => {
    return await axios
        .post(generateUrl(
            // "api/v1/user/auth?as_admin=true"
            "api/v1/user/auth/?as_admin=true"
        ), {
            ...data,
        })
        .then((res) => {
            setAccessToken(res.data.access_token);
            setRefreshToken(res.data.refresh_token);

            // ✅ ВИПРАВЛЕНО: Повертаємо весь response
            return res.data;
        })
        .catch((err) => ({
            error: err.response?.data?.detail || "Щось пішло не так.",
        }));
};