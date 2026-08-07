<template>
  <v-container fluid class="h-100 pa-4 bg-background" style="max-width: 1600px; margin: 0 auto;">

    <v-card class="mb-6 elevation-3" shaped>
      <v-card-title class="bg-primary text-white py-4 d-flex align-center justify-space-between">
        <div class="d-flex align-center">
          <v-icon start size="x-large" class="mr-3">mdi-dice-multiple</v-icon>
          <span class="text-h5 font-weight-bold">Shit Map Generator</span>
        </div>
        <v-btn color="white" variant="outlined" @click="copyPresetLink" prepend-icon="mdi-link-variant">
          Share Preset
        </v-btn>
      </v-card-title>

      <!-- RESULTS DISPLAY -->
      <v-card-text class="pa-6 bg-surface text-center">
        <div v-if="!currentResult" class="text-h5 text-medium-emphasis py-8">
          Configure your pools below and click Roll!
        </div>

        <v-row v-else class="align-center justify-center py-4" :class="{ 'animating-text': isRolling }">
          <v-col cols="12" md="4">
            <div class="text-caption text-uppercase text-medium-emphasis font-weight-bold mb-1">Map & Variant</div>
            <div class="text-h4 font-weight-bold text-primary mb-1">{{ currentResult.map }}</div>
            <v-chip size="small" color="primary" variant="tonal" class="font-weight-bold">
              {{ currentResult.variant }}
              <!-- Render the randomized Cap if it's a Domination map -->
              <template v-if="currentResult.cap">
                <span class="mx-2">|</span>
                <span class="text-amber-darken-2">Cap {{ currentResult.cap }}</span>
              </template>
            </v-chip>
          </v-col>
          <v-col cols="12" md="4" class="border-s border-e">
            <div class="text-caption text-uppercase text-medium-emphasis font-weight-bold mb-1">Time of Day</div>
            <div class="text-h4 font-weight-bold text-info">{{ currentResult.time }}</div>
          </v-col>
          <v-col cols="12" md="4">
            <div class="text-caption text-uppercase text-medium-emphasis font-weight-bold mb-1">Weather</div>
            <div class="text-h4 font-weight-bold text-success">{{ currentResult.weather }}</div>
          </v-col>
        </v-row>

        <div class="mt-6">
          <v-btn
            color="primary"
            size="x-large"
            elevation="4"
            @click="roll"
            :loading="isRolling"
            :disabled="!canRoll"
            prepend-icon="mdi-dice-5"
          >
            Roll Conditions
          </v-btn>
          <div v-if="!canRoll" class="text-error text-caption mt-2">
            You must select at least one option in every category to roll.
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- CONFIGURATION PANELS -->
    <v-row>
      <!-- MAP POOL -->
      <v-col cols="12" md="3">
        <v-card class="h-100 elevation-2">
          <v-card-title class="bg-blue-grey-darken-4 text-white d-flex justify-space-between align-center text-subtitle-1 py-2">
            <span><v-icon start>mdi-map</v-icon> Map Pool</span>
            <v-btn size="small" variant="text" @click="toggleAll('maps')">Toggle All</v-btn>
          </v-card-title>
          <v-card-text class="pt-4 overflow-y-auto" style="max-height: 500px;">
            <div v-if="isLoadingMaps" class="text-center py-4">
              <v-progress-circular indeterminate color="primary"></v-progress-circular>
            </div>
            <v-chip-group v-else v-model="activeMaps" multiple column selected-class="bg-primary text-white">
              <v-chip v-for="mapData in allMaps" :key="mapData.map_name" :value="mapData" filter variant="outlined">
                {{ mapData.map_name }}
              </v-chip>
            </v-chip-group>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- GAME MODES POOL -->
      <v-col cols="12" md="3">
        <v-card class="h-100 elevation-2">
          <v-card-title class="bg-blue-grey-darken-4 text-white d-flex justify-space-between align-center text-subtitle-1 py-2">
            <span><v-icon start>mdi-flag</v-icon> Allowed Modes</span>
            <v-btn size="small" variant="text" @click="toggleAll('modes')">Toggle All</v-btn>
          </v-card-title>
          <v-card-text class="pt-4 overflow-y-auto" style="max-height: 500px;">
            <v-chip-group v-model="activeModes" multiple column selected-class="bg-deep-purple text-white">
              <!-- Dynamically locked to the map pool -->
              <v-chip v-for="mode in availableModes" :key="mode" :value="mode" filter variant="outlined">
                {{ mode }}
              </v-chip>
            </v-chip-group>
            <div class="text-caption text-medium-emphasis mt-2" v-if="availableModes.length > 0">
              Only variants that actually exist on your selected maps are shown here.
            </div>
            <div class="text-caption text-error mt-2" v-else>
              Select at least one map to view its available game modes.
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- TIME POOL -->
      <v-col cols="12" md="3">
        <v-card class="h-100 elevation-2">
          <v-card-title class="bg-blue-grey-darken-4 text-white d-flex justify-space-between align-center text-subtitle-1 py-2">
            <span><v-icon start>mdi-clock</v-icon> Time Options</span>
            <v-btn size="small" variant="text" @click="toggleAll('times')">Toggle All</v-btn>
          </v-card-title>
          <v-card-text class="pt-4 overflow-y-auto" style="max-height: 500px;">
            <v-chip-group v-model="activeTimes" multiple column selected-class="bg-info text-white">
              <v-chip v-for="time in allTimes" :key="time" :value="time" filter variant="outlined">
                {{ time }}
              </v-chip>
            </v-chip-group>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- WEATHER POOL -->
      <v-col cols="12" md="3">
        <v-card class="h-100 elevation-2">
          <v-card-title class="bg-blue-grey-darken-4 text-white d-flex justify-space-between align-center text-subtitle-1 py-2">
            <span><v-icon start>mdi-weather-partly-cloudy</v-icon> Weather Options</span>
            <v-btn size="small" variant="text" @click="toggleAll('weather')">Toggle All</v-btn>
          </v-card-title>
          <v-card-text class="pt-4 overflow-y-auto" style="max-height: 500px;">
            <v-chip-group v-model="activeWeather" multiple column selected-class="bg-success text-white">
              <v-chip v-for="w in allWeather" :key="w" :value="w" filter variant="outlined">
                {{ w }}
              </v-chip>
            </v-chip-group>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- NOTIFICATION SNACKBAR -->
    <v-snackbar v-model="showSnackbar" color="success" timeout="2500" location="bottom">
      <v-icon start>mdi-check-circle</v-icon> Preset link copied to clipboard!
    </v-snackbar>

  </v-container>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue';

const isLoadingMaps = ref(true);
const showSnackbar = ref(false);

// --- STATIC DATA SOURCES ---
const allMaps = ref([]);

// Sorted alphabetically
const allTimes = ref([
  '07:00', '08:00', '09:00', '10:00', '11:00', '12:00',
  '13:00', '14:00', '15:00', '16:00', '17:00', '18:00',
  'Dawn', 'Day', 'Dusk', 'Evening', 'Morning', 'Night', 'Noon'
]);

// Sorted alphabetically
const allWeather = ref([
  'Clear', 'Cloudy', 'Fog', 'Hazy', 'Low Cloud Cover', 'Mist',
  'Overcast', 'Partly Cloudy', 'Rain', 'Storm', 'Thin Clouds',
  'Thunderclouds'
]);

// --- ACTIVE SELECTIONS ---
const activeMaps = ref([]);
const activeModes = ref([]);
const activeTimes = ref([]);
const activeWeather = ref([]);

// Consolidates identical modes into a single format to prevent duplicates
const formatVariantName = (variant) => {
  if (!variant) return 'Standard';
  let v = variant.trim();
  if (v.toLowerCase() === 'domination') return 'Domination #1';
  if (v.toLowerCase() === 'conquest') return 'Conquest #1';
  return v;
};

// --- DYNAMIC MODES LOGIC ---
// Computes ONLY the modes that exist across your currently selected activeMaps.
// The resulting array is inherently sorted alphabetically.
const availableModes = computed(() => {
  const modesSet = new Set();
  activeMaps.value.forEach(mapData => {
    if (mapData.variants) {
      Object.values(mapData.variants).forEach(variant => {
        if (variant.mode) modesSet.add(formatVariantName(variant.mode));
      });
    }
  });
  return Array.from(modesSet).sort();
});

// Watcher: If a map is unselected, clean up the activeModes so we don't hold invalid modes in the background
watch(availableModes, (newAvailable) => {
  activeModes.value = activeModes.value.filter(mode => newAvailable.includes(mode));
});

// Calculate which of the active maps actually possess at least one of the active modes
const validRollableMaps = computed(() => {
  return activeMaps.value.filter(mapData => {
    const mapVariants = Object.values(mapData.variants || {}).map(v => formatVariantName(v.mode));
    return mapVariants.some(vMode => activeModes.value.includes(vMode));
  });
});

// --- ROLLING LOGIC ---
const currentResult = ref(null);
const isRolling = ref(false);

const canRoll = computed(() => {
  return validRollableMaps.value.length > 0 &&
         activeTimes.value.length > 0 &&
         activeWeather.value.length > 0;
});

const toggleAll = (type) => {
  if (type === 'maps') {
    activeMaps.value = activeMaps.value.length === allMaps.value.length ? [] : [...allMaps.value];
  } else if (type === 'modes') {
    activeModes.value = activeModes.value.length === availableModes.value.length ? [] : [...availableModes.value];
  } else if (type === 'times') {
    activeTimes.value = activeTimes.value.length === allTimes.value.length ? [] : [...allTimes.value];
  } else if (type === 'weather') {
    activeWeather.value = activeWeather.value.length === allWeather.value.length ? [] : [...allWeather.value];
  }
};

const roll = () => {
  if (!canRoll.value) return;

  isRolling.value = true;
  let ticks = 0;
  const maxTicks = 20;

  const interval = setInterval(() => {
    // 1. Roll Map
    const randomMapData = validRollableMaps.value[Math.floor(Math.random() * validRollableMaps.value.length)];

    // 2. Roll Variant
    const mapVariants = Object.values(randomMapData.variants || {}).map(v => formatVariantName(v.mode));
    const validVariantsForThisMap = mapVariants.filter(vMode => activeModes.value.includes(vMode));
    const randomVariant = validVariantsForThisMap[Math.floor(Math.random() * validVariantsForThisMap.length)];

    // 3. Roll Domination Cap (A, B, or C) if applicable
    let selectedCap = null;
    if (randomVariant && randomVariant.toLowerCase().includes('domination')) {
      const caps = ['A', 'B', 'C'];
      selectedCap = caps[Math.floor(Math.random() * caps.length)];
    }

    currentResult.value = {
      map: randomMapData.map_name,
      variant: randomVariant,
      cap: selectedCap,
      time: activeTimes.value[Math.floor(Math.random() * activeTimes.value.length)],
      weather: activeWeather.value[Math.floor(Math.random() * activeWeather.value.length)],
    };

    ticks++;
    if (ticks >= maxTicks) {
      clearInterval(interval);
      isRolling.value = false;
    }
  }, 50);
};

// --- URL PRESET LOGIC ---
const copyPresetLink = () => {
  const params = new URLSearchParams();

  const mapNames = activeMaps.value.map(m => m.map_name).join(',');
  if (mapNames) params.set('maps', mapNames);
  if (activeModes.value.length) params.set('modes', activeModes.value.join(','));
  if (activeTimes.value.length) params.set('times', activeTimes.value.join(','));
  if (activeWeather.value.length) params.set('weather', activeWeather.value.join(','));

  const newUrl = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
  window.history.replaceState({}, '', newUrl);

  navigator.clipboard.writeText(newUrl).then(() => {
    showSnackbar.value = true;
  });
};

const applyUrlPresets = async () => {
  const params = new URLSearchParams(window.location.search);

  if (params.has('maps')) {
    const mapsParam = params.get('maps').split(',');
    activeMaps.value = allMaps.value.filter(m => mapsParam.includes(m.map_name));
  } else {
    activeMaps.value = [...allMaps.value];
  }

  // Wait for the computed availableModes property to dynamically update based on the maps we just set
  await nextTick();

  if (params.has('modes')) {
    const modesParam = params.get('modes').split(',');
    // We strictly filter against availableModes so bogus presets are ignored
    activeModes.value = modesParam.filter(m => availableModes.value.includes(m));
  } else {
    activeModes.value = [...availableModes.value];
  }

  if (params.has('times')) {
    activeTimes.value = params.get('times').split(',');
  } else {
    activeTimes.value = [...allTimes.value];
  }

  if (params.has('weather')) {
    activeWeather.value = params.get('weather').split(',');
  } else {
    activeWeather.value = [...allWeather.value];
  }
};

onMounted(async () => {
  try {
    const res = await fetch('/api/league/maps/data/');
    if (res.ok) {
      const data = await res.json();

      // Deduplicate backend maps to ensure no UI cloning
      const uniqueMaps = [];
      const mapNameSet = new Set();
      for (const m of data) {
        if (!mapNameSet.has(m.map_name)) {
          mapNameSet.add(m.map_name);
          uniqueMaps.push(m);
        }
      }

      // Sort maps alphabetically by map_name
      uniqueMaps.sort((a, b) => a.map_name.localeCompare(b.map_name));

      allMaps.value = uniqueMaps;

      await applyUrlPresets();
    }
  } catch (e) {
    console.error('Fetch error loading map JSONs:', e);
  } finally {
    isLoadingMaps.value = false;
  }
});
</script>

<style scoped>
.animating-text {
  filter: blur(1px);
  opacity: 0.7;
  transition: all 0.05s;
}
</style>