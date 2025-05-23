<template>
  <div class="register-container">
    <div class="register-box">
      <h1 class="register-title">Register</h1>
      <form @submit.prevent="register" class="register-form">
        <div class="form-group">
          <label for="username" class="form-label">Username</label>
          <input
            type="text"
            id="username"
            v-model="username"
            class="form-input"
            placeholder="Choose a username"
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
            placeholder="Create a password"
            required
          />
        </div>
        <div class="form-group">
          <label for="confirmPassword" class="form-label">Confirm Password</label>
          <input
            type="password"
            id="confirmPassword"
            v-model="confirmPassword"
            class="form-input"
            placeholder="Confirm your password"
            required
          />
        </div>
        <button type="submit" class="btn-submit">Register</button>
        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import {inject, ref} from 'vue';
import { useRouter } from 'vue-router';
import {fetchUserData} from "@/config/api/user.ts";
import { useUserStore } from '../config/store.ts';

const username = ref('');
const password = ref('');
const confirmPassword = ref('');
const errorMessage = ref('');
const router = useRouter();
const $cookies = inject("$cookies");
//@ts-ignore
const csrfToken = $cookies.get('csrftoken');
const userStore = useUserStore();

const register = async () => {
  if (password.value !== confirmPassword.value) {
    errorMessage.value = "Passwords do not match";
    return;
  }

  try {
    const response = await fetch('/api/user/register/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username.value,
        password: password.value,
        password2 : confirmPassword.value,
      }),
    });



    const data = await response.json();

    if (!response.ok) {
      throw new Error(`Registration failed: ${data.password}`);
    }

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

    router.push({ path: '/home' });
  } catch (error) {
    //@ts-ignore
    errorMessage.value = error.message;
  }
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--v-background-base);
  color: var(--v-text-primary);
}

.register-box {
  width: 100%;
  max-width: 400px;
  padding: 20px;
  border-radius: 8px;
  background-color: var(--v-surface);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.register-title {
  margin-bottom: 20px;
  font-size: 24px;
  color: var(--v-text-primary);
}

.register-form {
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