<template>
  <v-container class="mt-8">
    <!-- Hero Section -->
    <v-row justify="center" class="text-center mb-8">
      <v-col cols="12" md="10">
        <v-icon size="80" color="primary" class="mb-4">mdi-shield-star</v-icon>
        <h1 class="text-h2 font-weight-bold mb-4">Commander's Hub</h1>
        <p class="text-h6 text-grey-lighten-1">
          Your central command for team management, roster upgrades, and league operations.
        </p>
      </v-col>
    </v-row>

    <!-- Top Row: Discord & Documentation -->
    <v-row justify="center" class="mb-4">
      <!-- Discord Card -->
      <v-col cols="12" md="5">
        <v-card
          class="fill-height text-center py-6 interactive-card d-flex flex-column justify-center"
          elevation="3"
          :href="discordLink"
          target="_blank"
          rel="noopener"
        >
          <!-- Inlined Discord SVG ensures it renders perfectly regardless of Vite config -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            width="64"
            height="64"
            class="mx-auto mb-4"
            fill="#5865F2"
          >
            <path d="M22,24L16.75,19L17.38,21H4.5A2.5,2.5 0 0,1 2,18.5V3.5A2.5,2.5 0 0,1 4.5,1H19.5A2.5,2.5 0 0,1 22,3.5V24M12,6.8C9.32,6.8 7.44,7.95 7.44,7.95C8.47,7.03 10.27,6.5 10.27,6.5L10.1,6.33C8.41,6.36 6.88,7.53 6.88,7.53C5.16,11.12 5.27,14.22 5.27,14.22C6.67,16.03 8.75,15.9 8.75,15.9L9.46,15C8.21,14.73 7.42,13.62 7.42,13.62C7.42,13.62 9.3,14.9 12,14.9C14.7,14.9 16.58,13.62 16.58,13.62C16.58,13.62 15.79,14.73 14.54,15L15.25,15.9C15.25,15.9 17.33,16.03 18.73,14.22C18.73,14.22 18.84,11.12 17.12,7.53C17.12,7.53 15.59,6.36 13.9,6.33L13.73,6.5C13.73,6.5 15.53,7.03 16.56,7.95C16.56,7.95 14.68,6.8 12,6.8M9.93,10.59C10.58,10.59 11.11,11.16 11.1,11.86C11.1,12.55 10.58,13.13 9.93,13.13C9.29,13.13 8.77,12.55 8.77,11.86C8.77,11.16 9.28,10.59 9.93,10.59M14.1,10.59C14.75,10.59 15.27,11.16 15.27,11.86C15.27,12.55 14.75,13.13 14.1,13.13C13.46,13.13 12.94,12.55 12.94,11.86C12.94,11.16 13.45,10.59 14.1,10.59Z" />
          </svg>

          <v-card-title class="justify-center text-h5 font-weight-bold">Join the Discord</v-card-title>
          <v-card-text class="body-1 text-grey-lighten-1">
            Connect with other commanders, schedule matches, and get the latest announcements.
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Documentation Card -->
      <v-col cols="12" md="5">
        <v-card class="fill-height pb-2" elevation="3" rounded="lg">
          <v-card-title class="py-4 bg-surface-variant mb-2">
            <v-icon start color="blue-lighten-2">mdi-file-document-multiple-outline</v-icon>
            <span class="font-weight-bold">Official Documentation</span>
          </v-card-title>

          <v-list lines="two" bg-color="transparent">
            <!-- Vuetify 3 specific List formatting -->
            <v-list-item
              v-for="(doc, i) in documents"
              :key="i"
              :href="doc.url"
              target="_blank"
              rel="noopener"
              class="doc-link text-left"
            >
              <template v-slot:prepend>
                <v-icon :color="doc.color" class="mr-3" size="large">{{ doc.icon }}</v-icon>
              </template>

              <v-list-item-title class="font-weight-bold">{{ doc.title }}</v-list-item-title>
              <v-list-item-subtitle class="mt-1">{{ doc.subtitle }}</v-list-item-subtitle>

              <template v-slot:append>
                <v-icon size="small" color="grey">mdi-open-in-new</v-icon>
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <!-- Bottom Row: Randomizer & System Overview -->
    <v-row justify="center">
      <!-- Match Generation Tool Link -->
      <v-col cols="12" md="4">
        <v-card class="fill-height d-flex flex-column" elevation="3" rounded="lg">
          <v-card-title class="py-4 bg-surface-variant">
            <v-icon start color="orange-lighten-1">mdi-dice-multiple</v-icon>
            <span class="font-weight-bold">Match Generation</span>
          </v-card-title>
          <v-divider></v-divider>

          <v-card-text class="pt-6 flex-grow-1 d-flex flex-column justify-center align-center text-center">
            <v-icon size="64" color="orange-lighten-1" class="mb-4">mdi-slot-machine-outline</v-icon>
            <p class="mb-6 text-body-1 text-grey-lighten-1 px-4">
              Generate your maps, game modes, time of day, and weather all in one place with our newly integrated randomizer tool.
            </p>
            <!-- Update the 'to' prop to match your router's path for the Match Randomizer component -->
            <v-btn
              color="orange-darken-2"
              size="x-large"
              elevation="4"
              to="/maps"
              prepend-icon="mdi-launch"
              class="mt-auto mb-2"
            >
              Launch Randomizer
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- System Overview -->
      <v-col cols="12" md="6">
        <v-card class="fill-height" elevation="3" rounded="lg">
          <v-card-title class="py-4 bg-surface-variant">
            <v-icon start color="primary">mdi-information</v-icon>
            <span class="font-weight-bold">About the System</span>
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text class="pt-5 text-body-1">
            <p class="mb-4">This platform serves as the official management system for the league.</p>

            <ul class="feature-list text-left">
              <li class="d-flex align-start mb-4">
                <v-icon size="small" color="grey-lighten-1" class="mt-1 mr-3">mdi-package-variant</v-icon>
                <div><strong class="text-white">Manage Inventory:</strong> View your current vehicles, upgrade kits, and loot boxes.</div>
              </li>
              <li class="d-flex align-start mb-4">
                <v-icon size="small" color="grey-lighten-1" class="mt-1 mr-3">mdi-store</v-icon>
                <div><strong class="text-white">Visit the Store:</strong> Purchase tanks, sell hardware, and open boxes.</div>
              </li>
              <li class="d-flex align-start mb-4">
                <v-icon size="small" color="grey-lighten-1" class="mt-1 mr-3">mdi-wrench</v-icon>
                <div><strong class="text-white">Upgrade Vehicles:</strong> Utilize upgrade kits to climb the tech tree.</div>
              </li>
              <li class="d-flex align-start mb-4">
                <v-icon size="small" color="grey-lighten-1" class="mt-1 mr-3">mdi-chart-line</v-icon>
                <div><strong class="text-white">Track Matches:</strong> Review past match statistics, telemetry, and kill logs.</div>
              </li>
            </ul>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const discordLink = ref('https://discord.com/invite/gupev');

const documents = ref([
  {
    title: 'League Rules',
    subtitle: 'Official rulebook, formats, and conduct',
    icon: 'mdi-book-open-page-variant',
    color: 'blue-lighten-1',
    url: 'https://docs.google.com/document/d/1l4MlS6My2V4RvgpT6hLM9gQvN_HW59nG0dwdtyxhfgk'
  },
  {
    title: 'Judge / Match Rules',
    subtitle: 'Gameplay rules',
    icon: 'mdi-gavel',
    color: 'orange-lighten-1',
    url: 'https://docs.google.com/document/d/1hp7IrJ4nb1spqFC_J99Ef3bDLDaFuQvE3aaBfMRjvhQ/edit?usp=sharing'
  },
  {
    title: 'Spawn Points',
    subtitle: 'Map spawn areas',
    icon: 'mdi-map-marker-path',
    color: 'green-lighten-1',
    url: 'https://docs.google.com/document/d/1ATllZRk7JLVHDZo4KUtFoh_q_w_EZHBbi1B9sVt1WBc/edit?usp=sharing'
  },
]);
</script>

<style scoped>
.interactive-card {
  transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
  text-decoration: none;
}

.interactive-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important;
}

.doc-link {
  transition: background-color 0.2s ease;
  border-radius: 8px;
  margin-bottom: 4px;
}

.doc-link:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.feature-list {
  list-style-type: none;
  padding-left: 0;
  margin-top: 8px;
  margin-bottom: 8px;
}

.bg-surface-variant {
  background-color: rgba(255, 255, 255, 0.05) !important;
}
</style>