import router from "../../router/index.ts";
import { useUserStore } from "../store.ts";

const AUTH_TOKEN_KEY: string = "authToken";


export const fetchUserData = async () => {
  try {
    const userStore = useUserStore();
    const authToken = checkAuth();

    if (!authToken) {
      throw new Error("User is not authenticated");
    }

    const response = await fetch("/api/user/", {
      method: "GET",
      headers: {
        Authorization: `Token ${authToken}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        userStore.$reset();
        alert('You have been logged out');
      }
    }

    const data = await response.json();
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

export async function logout(csrfToken) {
    const userStore = useUserStore();
    console.log(getAuthToken());
    const response = await fetch('/api/user/logout/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
        'authorization': getAuthToken(),
      },
    });
    if (response.status == 204){
      userStore.$reset()
      localStorage.removeItem(AUTH_TOKEN_KEY);
      console.log("User successfully logged out")
    }
}

export const checkAuth = () => {
  const authToken = isAuthenticated();

  if (authToken) {
    let date = new Date().getTime();
    date += 3600000*24;
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