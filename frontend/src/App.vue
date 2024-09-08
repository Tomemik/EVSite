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