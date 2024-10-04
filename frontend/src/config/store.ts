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