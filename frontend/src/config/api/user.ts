import router from "../../router/index.ts";
import { useUserStore } from "../store.ts";

const AUTH_HEADER_NAME: string = "auth-token";
const AUTH_TOKEN_KEY: string = "authToken";

export const fetchUserData = async () => {
  try {
    const userStore = useUserStore();
    const response = await fetch("/api/user/", {
      method: "GET",
      headers: {
        "Authorization": getAuthToken(),
      },
    });
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    console.log(data)
    userStore.username = data.username;
    userStore.groups = data.groups;
    if (data.team) {
        userStore.team = data.team.name;
    }
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
  router.push({ name: "Login" });
  return false;
};

export const getAuthToken = (): string => {
  const token = checkAuth();
  return `Token ${token}`;
};