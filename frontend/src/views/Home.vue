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

    <!-- Bottom Row: Wheels & System Overview -->
    <v-row justify="center">
      <!-- Match Generation Wheels -->
      <v-col cols="12" md="4">
        <v-card class="fill-height" elevation="3" rounded="lg">
          <v-card-title class="py-4 bg-surface-variant">
            <v-icon start color="orange-lighten-1">mdi-slot-machine-outline</v-icon>
            <span class="font-weight-bold">Match Generation</span>
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text class="pt-4">
            <p class="mb-5 text-body-2 text-grey-lighten-1 text-center">
              Use these tools to randomly determine parameters for your upcoming matches.
            </p>
            <v-row dense>
              <v-col cols="6" v-for="(wheel, i) in wheels" :key="i">
                <v-btn
                  block
                  variant="tonal"
                  :color="wheel.color"
                  class="wheel-btn h-100 py-3"
                  :href="wheel.url"
                  target="_blank"
                  rel="noopener"
                >
                  <div class="d-flex flex-column align-center">
                    <v-icon class="mb-2" size="x-large">{{ wheel.icon }}</v-icon>
                    <span class="text-caption font-weight-bold">{{ wheel.title }}</span>
                  </div>
                </v-btn>
              </v-col>
            </v-row>
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

const wheels = ref([
  {
    title: 'Maps',
    icon: 'mdi-map',
    color: 'success',
    url: "https://wheeldecide.com/index.php?c1=abandoned+factory&c2=advance+to+the+rhine&c3=alaska&c4=american+desert&c5=ardennes&c6=ash+river+&c7=Battle+of+Hürtgen+Forest&c8=Berlin&c9=Cargo+Port&c10=Carpathians&c11=Eastern+Europe&c12=European+Province&c13=Finland&c14=Frozen+Pass&c15=Fulda+Gap&c16=Emperor's+Garden&c17=Jungle&c18=Karelia&c19=38th+Parallel&c20=Kuban&c21=Kursk&c22=Maginot+Line&c23=Middle+East&c24=Mozdok&c25=Fields+of+Normandy&c26=+Poland&c27=Fields+of+Poland&c28=Port+Novorossiysk&c29=Second+Battle+of+El+Alamein&c30=Sinai&c31=Sands+of+Sinai&c32=Stalingrad&c33=Tunisia&c34=Sands+of+Tunisia&c35=Vietnam+Hills&c36=Volokolamsk&c37=Red+Desert&c38=Sweden&c39=Seversk-13&c40=Spaceport&c41=Breslau&c42=White+rock+fortress&c43=Aral+sea&c44=Sun+City&c45=Ground+Zero&c46=Abandoned+Town&c47=Arctic&c48=Golden+Quarry&c49=Winter+Poland&c50=Winter+Fields+of+Poland&c51=Normandy&c52=Campania&c53=Winter+Seversk&c54=Winter+Maginot&c55=Winter+Ardennes&c56=Iberian+Castle&c57=Pradesh&c58=Test+Site+2771&c59=Flanders&t=Trash+Maps+Generator&time=5"
  },
  {
    title: 'Conquest',
    icon: 'mdi-flag-variant',
    color: 'error',
    url: 'https://wheeldecide.com/index.php?c1=Conquest+1&c2=Conquest+2&c3=Conquest+3&c4=Conquest+4&t=Conquest&time=5'
  },
  {
    title: 'Time',
    icon: 'mdi-clock-outline',
    color: 'primary',
    url: 'https://wheeldecide.com/index.php?c1=Dawn&c2=Morning&c3=Noon&c4=Day&c5=Evening&c6=Dusk&c7=07%3A00&c8=08%3A00&c9=09%3A00&c10=10%3A00&c11=11%3A00&c12=12%3A00&c13=13%3A00&c14=14%3A00&c15=15%3A00&c16=16%3A00&c17=17%3A00&c18=18%3A00&c19=Night&t=Wheel+of+Time&time=5'
  },
  {
    title: 'Weather',
    icon: 'mdi-weather-partly-cloudy',
    color: 'info',
    url: 'https://wheeldecide.com/index.php?c1=Clear&c2=Partly+Cloudy&c3=Hazy&c4=Mist&c5=Thin+Clouds&c6=Thunderclouds&c7=Cloudy&c8=Overcast&c9=Low+Cloud+Cover&c10=Fog&c11=Rain&c12=Storm&t=Wheel+of+Weather&time=5'
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

.wheel-btn {
  transition: transform 0.1s ease;
}

.wheel-btn:hover {
  transform: scale(1.03);
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