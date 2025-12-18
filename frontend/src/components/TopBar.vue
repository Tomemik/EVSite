<template>
  <v-app>
    <v-app-bar color="primary" prominent>
      <v-app-bar-nav-icon variant="text" @click.stop="drawer = !drawer"></v-app-bar-nav-icon>

      <v-toolbar-title>GuP EV</v-toolbar-title>

      <v-spacer></v-spacer>

      <v-toolbar-items v-if="isUserLoggedIn" class="hidden-xs-only">
        <v-btn
          flat
          v-for="item in barItemsLoggedIn"
          :key="item.title"
          :to="item.path"
          variant="text"
        >
          <v-icon right>{{ item.icon }}</v-icon>
          {{ item.title }}
        </v-btn>
        <v-btn
          flat
          variant="text"
          @click="logout(csrfToken)"
        >
          <v-icon right>{{ 'mdi-logout' }}</v-icon>
           log-out
        </v-btn>
        <v-btn @click="toggleTheme">toggle theme</v-btn>
      </v-toolbar-items>

      <v-toolbar-items v-else class="hidden-xs-only">
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
        <v-btn @click="toggleTheme">toggle theme</v-btn>
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
import {inject, ref, watch} from 'vue';
import {isAuthenticated, fetchUserData, logout} from "../config/api/user.ts";
import {useUserStore} from "../config/store.ts";
const $cookies = inject("$cookies");
//@ts-ignore
const csrfToken = $cookies.get('csrftoken');
const isUserLoggedIn = ref(isAuthenticated())
const userStore = useUserStore()
import { useTheme } from 'vuetify'

const theme = useTheme()

function toggleTheme () {
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
}

const drawer = ref<boolean>(false);

const barItems = ref([
  { title: 'Log-in', path: '/login', icon: 'mdi-login' },
  { title: 'Register', path: '/register'},
]);

const barItemsLoggedIn = ref([
  {title: '', path:'/', icon:''},
]);

const drawerItems = ref([
  { title: 'Teams', path: '/teams' },
  { title: 'Team Tanks', path: '/teamtanks'},
  { title: 'Imports', path: '/imports'},
  { title: 'Boxes', path: '/boxes' },
  { title: 'Matches', path: '/matches' },
  { title: 'Money Log', path: '/log'},
  { title: 'Tanks', path: '/tanks' },
  { title: 'Manufacturers', path: '/manufacturers' },
  { title: 'Upgrade Charts', path: '/upgrades' },
  { title: 'Interchangeability Charts', path: '/interchangeability' },
]);

watch(
  () => userStore.username,
  (newVal) => {
    isUserLoggedIn.value = !!newVal;
  },
  { immediate: true }
);

if (isUserLoggedIn.value) {
  fetchUserData().catch(error => {
    console.error("Error fetching user data:", error);
    isUserLoggedIn.value = false;
  });
}

</script>

<style scoped>
.main-content {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  overflow: auto;
}

@media (max-width: 600px) {
  .main-content {
    height: calc(100vh - 56px);
  }
}
</style>