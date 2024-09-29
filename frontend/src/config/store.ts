import { defineStore } from "pinia";

export const useUserStore = defineStore("user", {
  state: () => ({
    username: "",
    roles: [],
  }) as {
    username: string;
    roles: string[];
  },
});