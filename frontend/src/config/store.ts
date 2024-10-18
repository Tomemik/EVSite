import { defineStore } from "pinia";

export const useUserStore = defineStore("user", {
  state: () => ({
    username: "",
    groups: [],
    team: "",
  }) as {
    username: string;
    groups: string[];
    team: string;
  },
  persist: true
});

export const useSettingsStore = defineStore("settings", {
  state: () => ({
    filterTeams: [useUserStore().team],
  }) as {
    filterTeams: string[];
  },
  persist: true
})