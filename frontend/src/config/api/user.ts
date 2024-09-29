import router, { saveRouteToRedirect } from "./router";
import { useUserStore } from "../store";

const AUTH_HEADER_NAME: string = "auth-token";
const AUTH_TOKEN_KEY: string = "authToken";
const userStore = useUserStore();

export const fetchUserData = async () => {
  try {
    const response = await fetch("/api/user/", {
      method: "GET",
      headers: {
        "api-auth": getAuthToken(),
      },
    });
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    await response.json();
    console.log(response);
    userStore.username = response.username;
    userStore.roles = response.roles
  } catch (error) {
    console.error("Failed to fetch user data:", error);
    throw error;
  }
};

export function isAuthenticated() {
  const authToken = localStorage.getItem(AUTH_TOKEN_KEY);
  if (authToken && JSON.parse(authToken).expDate > new Date().getTime()) {
    return authToken;
  }
  return false;
}

export const checkAuth = () => {
  const authToken = isAuthenticated();

  if (authToken) {
    let date = new Date().getTime();
    date += 1800000;
    localStorage.setItem(
      AUTH_TOKEN_KEY,
      JSON.stringify({
        token: JSON.parse(authToken).token,
        expDate: date,
        username: JSON.parse(authToken).username,
      }),
    );
    return JSON.parse(authToken).token;
  }
  localStorage.removeItem(AUTH_TOKEN_KEY);
  saveRouteToRedirect(router.currentRoute.value);
  router.push({ name: "Login" });
  return false;
};

export const getAuthToken = (): string => {
  const token = checkAuth();
  return `Token ${token}`;
};