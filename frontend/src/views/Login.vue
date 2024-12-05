<template>
  <div class="login-container">
    <div class="login-box">
      <h1 class="login-title">Login</h1>
      <form @submit.prevent="login" class="login-form">
        <div class="form-group">
          <label for="username" class="form-label">Username</label>
          <input
            type="text"
            id="username"
            v-model="username"
            class="form-input"
            placeholder="Enter your username"
            required
          />
        </div>
        <div class="form-group">
          <label for="password" class="form-label">Password</label>
          <input
            type="password"
            id="password"
            v-model="password"
            class="form-input"
            placeholder="Enter your password"
            required
          />
        </div>
        <button type="submit" class="btn-submit">Login</button>
        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
      </form>
      <p class="redirect-message">
        Don't have an account?
        <router-link to="/register" class="redirect-link">Register here</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import {inject, onMounted, ref} from 'vue';
import { useUserStore } from '../config/store.ts';
import { fetchUserData } from '../config/api/user.ts';
import { useRouter } from 'vue-router';

const username = ref('');
const password = ref('');
const errorMessage = ref('');
const router = useRouter();
const userStore = useUserStore();
const $cookies = inject("$cookies");
//@ts-ignore
const csrfToken = $cookies.get('csrftoken');

const login = async () => {
  try {
    const response = await fetch('/api/user/login/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username.value,
        password: password.value,
      }),
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.statusText}`);
    }

    const data = await response.json();
    userStore.username = username.value;
    let expiryDate = new Date().getTime() + 1800000;
    localStorage.setItem(
      "authToken",
      JSON.stringify({
        token: data.token,
        expDate: expiryDate,
        username: username.value,
      }),
    );
    await fetchUserData();

    router.go(0);

  } catch (error) {
    //@ts-ignore
    errorMessage.value = error.message;
  }
};

function checkAuthTokenTimeout() {
  const authTokenData = localStorage.getItem("authToken");

  if (authTokenData) {
    const { expDate } = JSON.parse(authTokenData);
    const currentTime = new Date().getTime();

    if (currentTime > expDate) {
      localStorage.removeItem("authToken");
      userStore.$reset();
    }
    return
  }
  userStore.$reset();}

onMounted(() => {
  checkAuthTokenTimeout()
  console.log(userStore.username)
  if (userStore.username) {
    router.push('/home')
  }
})

</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--v-background-base);
  color: var(--v-text-primary);
}

.login-box {
  width: 100%;
  max-width: 400px;
  padding: 20px;
  border-radius: 8px;
  background-color: var(--v-surface);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.login-title {
  margin-bottom: 20px;
  font-size: 24px;
  color: var(--v-text-primary);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.form-label {
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--v-text-secondary);
}

.form-input {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid var(--v-divider);
  border-radius: 4px;
  background-color: var(--v-surface);
  color: var(--v-text-primary);
  transition: border-color 0.3s;
}

.form-input:focus {
  border-color: var(--v-primary);
  outline: none;
}

.btn-submit {
  width: 100%;
  padding: 12px;
  font-size: 16px;
  color: var(--v-text-primary-inverse);
  background-color: var(--v-primary);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.btn-submit:hover {
  background-color: var(--v-primary-darken1);
}

.error-message {
  margin-top: 10px;
  color: var(--v-error);
  font-size: 14px;
}
</style>