<template>
  <v-app>
    <v-app-bar color="primary" prominent>
      <v-app-bar-nav-icon variant="text" @click.stop="drawer = !drawer"></v-app-bar-nav-icon>

      <v-toolbar-title>GuP EV</v-toolbar-title>

      <v-spacer></v-spacer>

      <v-toolbar-items class="hidden-xs-only">
        <v-btn
          flat
          v-for="item in barItems"
          :key="item.title"
          :to="item.path"
          variant="text"
        >
          <v-icon right>{{ item.icon }}</v-icon>
          {{ item.title }}
        </v-btn>
      </v-toolbar-items>
    </v-app-bar>

    <v-navigation-drawer v-model="drawer" temporary>
      <v-list>
        <v-list-item
          v-for="item in drawerItems"
          :key="item.title"
          :to="item.path"
          router
        >
          <v-list-item-title>{{ item.title }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-main class="main-content">
      <router-view></router-view>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const drawer = ref<boolean>(false);

const barItems = ref([
  { title: 'Log-in', path: '/login', icon: 'mdi-login' },
]);

const drawerItems = ref([
  { title: 'Teams', path: '/teams' },
  { title: 'Tanks', path: '/tanks' },
  { title: 'Manufacturers', path: '/manufacturers' },
  { title: 'Matches', path: '/matches' },
]);
</script>

<style scoped>
.main-content {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px); /* Adjust if app-bar height changes */
  overflow: auto;
}

/* Optional: Adjust for better mobile view */
@media (max-width: 600px) {
  .main-content {
    height: calc(100vh - 56px); /* Adjust if app-bar height changes */
  }
}
</style>