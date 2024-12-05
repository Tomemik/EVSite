<template>
  <VApp class="app-container">
    <VMain class="main-container">
      <TopBar></TopBar>
      <!-- Other content here -->
    </VMain>
  </VApp>
</template>

<script setup lang="ts">
import TopBar from "./components/TopBar.vue";
import {onMounted} from "vue";
import {useUserStore} from "@/config/store.ts";
import {fetchUserData} from "@/config/api/user.ts";

const userStore = useUserStore()

function checkAuthTokenTimeout() {
  const authTokenData = localStorage.getItem("authToken");

  if (authTokenData) {
    const { expDate } = JSON.parse(authTokenData);
    const currentTime = new Date().getTime();


    if (currentTime >= expDate) {
      localStorage.removeItem("authToken");
      userStore.$reset();
    }
    return
  }
  userStore.$reset();
}


onMounted(() => {
  checkAuthTokenTimeout()
  fetchUserData()
})

</script>

<style scoped>
.app-container {
  height: 100vh; /* Full viewport height */
  overflow: hidden; /* Prevent overflow on VApp */
}

.main-container {
  height: 100%; /* Full height of the VApp */
  overflow: auto; /* Allow scrolling if content overflows */
}
</style>