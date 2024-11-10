<template>
  <div class="login">
    <h1>Login</h1>
    <form @submit.prevent="login">
      <div>
        <label for="username">Username:</label>
        <input
          type="text"
          id="username"
          v-model="username"
          required
        />
      </div>
      <div>
        <label for="password">Password:</label>
        <input
          type="password"
          id="password"
          v-model="password"
          required
        />
      </div>
      <button type="submit">Login</button>
      <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
    </form>
  </div>
</template>

<script setup lang="ts">
import {inject, ref} from 'vue';
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
    router.push({ name: 'Home' });
  } catch (error) {
    //@ts-ignore
    errorMessage.value = error.message;
  }
};
</script>

<style scoped>
.login {
  max-width: 300px;
  margin: auto;
}
.error {
  color: red;
}
</style>