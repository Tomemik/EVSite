<template>
  <v-container fluid class="h-100 d-flex flex-column pa-4 bg-background" style="margin: 0 auto;">

    <v-card class="mb-4 elevation-2 flex-shrink-0" shaped>
      <v-card-title class="d-flex justify-space-between align-center primary white--text py-4 bg-primary">
        <div class="d-flex align-center">
          <v-icon start size="x-large" class="mr-3">mdi-poll</v-icon>
          <div>
            <span class="text-h5 font-weight-bold">Vehicle Statistics</span>
          </div>
        </div>
        <v-btn color="white" variant="outlined" @click="forceReload" :loading="isLoading">
          <v-icon start>mdi-refresh</v-icon> Refresh Data
        </v-btn>
      </v-card-title>

      <v-toolbar color="surface" density="compact" class="border-b px-2">
        <v-tabs v-model="activeTab" color="primary">
          <v-tab value="vehicles"><v-icon start>mdi-tank</v-icon> Played Vehicles</v-tab>
          <v-tab value="all_tanks"><v-icon start>mdi-database</v-icon> All DB Tanks</v-tab>
          <v-tab v-if="isAdmin" value="players"><v-icon start>mdi-account-group</v-icon> Players</v-tab>
        </v-tabs>
        <v-spacer></v-spacer>

        <v-btn
          variant="tonal"
          color="info"
          prepend-icon="mdi-filter-variant"
          @click="showFilters = !showFilters"
          class="mr-4"
        >
          Advanced Filters
        </v-btn>

        <div style="width: 350px;" class="my-2">
          <v-text-field
            v-model="searchQuery"
            label="Search name, vehicle, etc..."
            prepend-inner-icon="mdi-magnify"
            density="compact"
            variant="solo-filled"
            flat
            hide-details
            clearable
          ></v-text-field>
        </div>
      </v-toolbar>

      <v-expand-transition>
        <v-card v-if="showFilters" color="grey-darken-4" class="px-4 pb-4 pt-8 border-b rounded-0" flat theme="dark">
          <v-row dense align="center">
            <v-col cols="12" md="3" class="px-4">
              <v-range-slider
                v-model="filterBr"
                min="0.3"
                max="8.5"
                step="0.1"
                label="BR Range"
                thumb-label="always"
                density="compact"
                hide-details
                color="info"
              ></v-range-slider>
            </v-col>
            <v-col cols="12" md="2">
              <v-select
                v-model="filterType"
                :items="['LT', 'MT', 'HT', 'TD']"
                label="Tank Class"
                density="compact"
                variant="outlined"
                hide-details
                clearable
              ></v-select>
            </v-col>
            <v-col cols="12" md="2">
              <v-select
                v-model="filterRank"
                :items="[1, 2, 3, 4, 5, 6]"
                label="Rank"
                density="compact"
                variant="outlined"
                hide-details
                clearable
              ></v-select>
            </v-col>
            <v-col cols="12" md="2">
              <v-select
                v-model="filterTier"
                :items="[
                  {title:'Top Tier (Max BR)', value:'top'},
                  {title:'Mid Tier (-0.3 to -1.0)', value:'mid'},
                  {title:'Bottom Tier (-1.3+)', value:'bottom'}
                ]"
                label="Match Tier Context"
                density="compact"
                variant="outlined"
                hide-details
                clearable
              ></v-select>
            </v-col>
            <v-col cols="12" md="3">
              <v-autocomplete
                v-model="filterTeam"
                :items="availableTeams"
                item-title="name"
                item-value="name"
                label="Played By Team"
                density="compact"
                variant="outlined"
                hide-details
                clearable
              ></v-autocomplete>
            </v-col>
          </v-row>
        </v-card>
      </v-expand-transition>
    </v-card>

    <v-card class="flex-grow-1 overflow-hidden elevation-2 d-flex flex-column">
      <v-window v-model="activeTab" class="h-100 overflow-auto">

        <!-- PLAYED VEHICLES TAB -->
        <v-window-item value="vehicles">
          <v-data-table-server
            :headers="vehicleHeaders"
            :items="serverItems"
            :items-length="totalItems"
            :loading="isLoading"
            :search="searchQuery"
            items-per-page="25"
            hover
            striped
            fixed-header
            density="comfortable"
            @update:options="loadItems"
            @click:row="openVehicleDetails"
            class="clickable-rows h-100"
          >
            <template v-slot:[`item.match_winrate`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getWinrateColor(item.match_winrate)}`">{{ item.match_winrate }}%</span>
            </template>
            <template v-slot:[`item.round_winrate`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getWinrateColor(item.round_winrate)}`">{{ item.round_winrate }}%</span>
            </template>
            <template v-slot:[`item.kd_ratio`]="{ item }">
              <v-chip size="small" :color="getRatioColor(item.kd_ratio)" class="font-weight-bold">{{ item.kd_ratio.toFixed(2) }}</v-chip>
            </template>
            <template v-slot:[`item.kills_per_spawn`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getRatioColor(item.kills_per_spawn)}`">{{ item.kills_per_spawn.toFixed(2) }}</span>
            </template>
          </v-data-table-server>
        </v-window-item>

        <!-- ALL DB TANKS TAB -->
        <v-window-item value="all_tanks">
          <v-data-table-server
            :headers="allTanksHeaders"
            :items="serverItems"
            :items-length="totalItems"
            :loading="isLoading"
            :search="searchQuery"
            items-per-page="25"
            hover
            striped
            fixed-header
            density="comfortable"
            @update:options="loadItems"
            @click:row="openVehicleDetails"
            class="clickable-rows h-100"
          >
            <template v-slot:[`item.participation_rate`]="{ item }">
              <v-chip size="small" color="info" class="font-weight-bold" variant="tonal">{{ item.participation_rate }}%</v-chip>
            </template>
            <template v-slot:[`item.match_winrate`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getWinrateColor(item.match_winrate)}`">{{ item.match_winrate }}%</span>
            </template>
            <template v-slot:[`item.round_winrate`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getWinrateColor(item.round_winrate)}`">{{ item.round_winrate }}%</span>
            </template>
            <template v-slot:[`item.kd_ratio`]="{ item }">
              <v-chip size="small" :color="getRatioColor(item.kd_ratio)" class="font-weight-bold">{{ item.kd_ratio.toFixed(2) }}</v-chip>
            </template>
            <template v-slot:[`item.kills_per_spawn`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getRatioColor(item.kills_per_spawn)}`">{{ item.kills_per_spawn.toFixed(2) }}</span>
            </template>
          </v-data-table-server>
        </v-window-item>

        <!-- PLAYERS TAB -->
        <v-window-item v-if="isAdmin" value="players">
          <v-data-table-server
            :headers="playerHeaders"
            :items="serverItems"
            :items-length="totalItems"
            :loading="isLoading"
            :search="searchQuery"
            items-per-page="25"
            hover
            striped
            fixed-header
            density="comfortable"
            @update:options="loadItems"
            @click:row="openPlayerDetails"
            class="clickable-rows h-100"
          >
            <template v-slot:[`item.match_winrate`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getWinrateColor(item.match_winrate)}`">{{ item.match_winrate }}%</span>
            </template>
            <template v-slot:[`item.round_winrate`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getWinrateColor(item.round_winrate)}`">{{ item.round_winrate }}%</span>
            </template>
            <template v-slot:[`item.kd_ratio`]="{ item }">
              <v-chip size="small" :color="getRatioColor(item.kd_ratio)" class="font-weight-bold">{{ item.kd_ratio.toFixed(2) }}</v-chip>
            </template>
            <template v-slot:[`item.kills_per_spawn`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getRatioColor(item.kills_per_spawn)}`">{{ item.kills_per_spawn.toFixed(2) }}</span>
            </template>
          </v-data-table-server>
        </v-window-item>
      </v-window>
    </v-card>

    <!-- VEHICLE DRILLDOWN DIALOG -->
    <v-dialog v-model="showVehicleDialog" max-width="850px" scrollable>
      <v-card v-if="selectedVehicle" max-height="90vh" class="d-flex flex-column">
        <v-card-title class="bg-primary text-white d-flex justify-space-between align-center flex-shrink-0">
          <span><v-icon start color="white">mdi-tank</v-icon> {{ selectedVehicle.name }}</span>
          <v-btn icon="mdi-close" variant="text" color="white" @click="showVehicleDialog = false"></v-btn>
        </v-card-title>

        <v-card-text class="pt-6 overflow-y-auto">
          <v-row class="text-center mb-4" justify="space-around">
            <v-col cols="auto" v-if="selectedVehicle.participation_rate !== undefined">
              <div class="text-caption text-medium-emphasis">Usage Rate</div>
              <div class="text-h6 text-info">{{ selectedVehicle.participation_rate }}%</div>
            </v-col>
            <v-col cols="auto">
              <div class="text-caption text-medium-emphasis">Match WR</div>
              <div class="text-h6" :class="`text-${getWinrateColor(selectedVehicle.match_winrate)}`">{{ selectedVehicle.match_winrate }}%</div>
            </v-col>
            <v-col cols="auto">
              <div class="text-caption text-medium-emphasis">Round WR</div>
              <div class="text-h6" :class="`text-${getWinrateColor(selectedVehicle.round_winrate)}`">{{ selectedVehicle.round_winrate }}%</div>
            </v-col>
            <v-col cols="auto">
              <div class="text-caption text-medium-emphasis">Total Spawns</div>
              <div class="text-h6">{{ selectedVehicle.spawns }}</div>
            </v-col>
            <v-col cols="auto">
              <div class="text-caption text-medium-emphasis">Kills</div>
              <div class="text-h6 text-success">{{ selectedVehicle.kills }}</div>
            </v-col>
          </v-row>

          <v-divider v-if="isAdmin" class="my-4"></v-divider>

          <div v-if="isAdmin">
            <h3 class="text-subtitle-1 font-weight-bold mb-3">Player Drilldown</h3>

            <v-autocomplete
              v-model="selectedFilterPlayers"
              :items="sortedVehiclePlayers"
              item-title="title"
              item-value="value"
              label="Select players to view specific performance"
              prepend-inner-icon="mdi-account-search"
              variant="outlined"
              density="comfortable"
              multiple
              chips
              closable-chips
              clearable
            ></v-autocomplete>

            <v-expand-transition>
              <v-alert
                v-if="aggregatedComboStats && selectedFilterPlayers.length > 1"
                color="indigo-darken-4"
                theme="dark"
                class="mt-4 mb-6 border"
                border="start"
                border-color="info"
              >
                <div class="d-flex justify-space-between align-center">
                  <div>
                    <div class="text-subtitle-1 font-weight-bold">Aggregated Selection Stats</div>
                    <div class="text-caption text-medium-emphasis">{{ selectedFilterPlayers.length }} players combined</div>
                    <div class="mt-2">
                      <v-chip size="small" class="mr-2">Total Spawns: {{ aggregatedComboStats.spawns }}</v-chip>
                      <v-chip size="small" color="success" class="mr-2">Total Kills: {{ aggregatedComboStats.kills }}</v-chip>
                      <v-chip size="small" color="error">Total Deaths: {{ aggregatedComboStats.deaths }}</v-chip>
                    </div>
                  </div>
                  <div class="text-right d-flex align-center">
                    <div class="mr-6 text-right">
                      <div class="text-caption">Agg. Round WR</div>
                      <div class="text-h6 font-weight-bold" :class="`text-${getWinrateColor(aggregatedComboStats.round_winrate)}`">
                        {{ aggregatedComboStats.round_winrate.toFixed(1) }}%
                      </div>
                    </div>
                    <div class="mr-4 text-right">
                      <div class="text-caption">Avg K/S</div>
                      <div class="text-h6 font-weight-bold">{{ aggregatedComboStats.kills_per_spawn.toFixed(2) }}</div>
                    </div>
                    <div class="text-right">
                      <div class="text-caption">Total K/D</div>
                      <div class="text-h5 font-weight-bold" :class="`text-${getRatioColor(aggregatedComboStats.kd_ratio)}`">
                        {{ aggregatedComboStats.kd_ratio.toFixed(2) }}
                      </div>
                    </div>
                  </div>
                </div>
              </v-alert>
            </v-expand-transition>

            <div class="d-flex flex-column mt-4" style="gap: 12px;">
              <v-slide-y-transition group>
                <v-alert v-for="combo in activeComboStatsList" :key="combo.player" color="blue-grey-darken-4" theme="dark" class="ma-0">
                  <div class="d-flex justify-space-between align-center">
                    <div>
                      <div class="text-subtitle-2 text-medium-emphasis">Performance: <strong class="text-white">{{ combo.player }}</strong></div>
                      <div class="mt-2">
                        <v-chip size="small" class="mr-2">Match WR: {{ combo.match_winrate }}%</v-chip>
                        <v-chip size="small" class="mr-2">Round WR: {{ combo.round_winrate }}%</v-chip>
                        <v-chip size="small" color="success" class="mr-2">Kills: {{ combo.kills }}</v-chip>
                        <v-chip size="small" color="error">Deaths: {{ combo.deaths }}</v-chip>
                      </div>
                    </div>
                    <div class="text-right d-flex align-center">
                      <div class="mr-4 text-right">
                        <div class="text-caption">K/S</div>
                        <div class="text-subtitle-1 font-weight-bold" :class="`text-${getRatioColor(combo.kills_per_spawn)}`">{{ combo.kills_per_spawn.toFixed(2) }}</div>
                      </div>
                      <div class="text-right">
                        <div class="text-caption">K/D Ratio</div>
                        <div class="text-h5 font-weight-bold" :class="`text-${getRatioColor(combo.kd_ratio)}`">
                          {{ combo.kd_ratio.toFixed(2) }}
                        </div>
                      </div>
                    </div>
                  </div>
                </v-alert>
              </v-slide-y-transition>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- PLAYER DRILLDOWN DIALOG -->
    <v-dialog v-model="showPlayerDialog" max-width="900px" scrollable>
      <v-card v-if="selectedPlayer" max-height="90vh" class="d-flex flex-column">
        <v-card-title class="bg-indigo-darken-3 text-white d-flex justify-space-between align-center flex-shrink-0">
          <span><v-icon start color="white">mdi-account</v-icon> {{ selectedPlayer.name }}</span>
          <v-btn icon="mdi-close" variant="text" color="white" @click="showPlayerDialog = false"></v-btn>
        </v-card-title>

        <v-card-text class="pt-6 overflow-y-auto">
          <v-row class="text-center mb-4">
            <v-col cols="3">
              <v-card class="pa-3 elevation-1" color="grey-darken-4">
                <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">Match WR</div>
                <div class="text-h5" :class="`text-${getWinrateColor(selectedPlayer.match_winrate)}`">{{ selectedPlayer.match_winrate }}%</div>
              </v-card>
            </v-col>
            <v-col cols="3">
              <v-card class="pa-3 elevation-1" color="grey-darken-4">
                <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">Round WR</div>
                <div class="text-h5" :class="`text-${getWinrateColor(selectedPlayer.round_winrate)}`">{{ selectedPlayer.round_winrate }}%</div>
              </v-card>
            </v-col>
            <v-col cols="3">
              <v-card class="pa-3 elevation-1" color="grey-darken-4">
                <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">Total Kills</div>
                <div class="text-h5 text-success">{{ selectedPlayer.kills }}</div>
              </v-card>
            </v-col>
            <v-col cols="3">
              <v-card class="pa-3 elevation-1" color="grey-darken-4">
                <div class="text-caption text-medium-emphasis text-uppercase font-weight-bold">Total Deaths</div>
                <div class="text-h5 text-error">{{ selectedPlayer.deaths }}</div>
              </v-card>
            </v-col>
          </v-row>

          <h3 class="text-subtitle-1 font-weight-bold mb-3 mt-6">Vehicles Driven</h3>

          <div v-if="isPlayerDialogLoading" class="d-flex justify-center my-6">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
          </div>

          <v-data-table
            v-if="!isPlayerDialogLoading"
            :headers="playerVehiclesHeaders"
            :items="playerVehiclesList"
            items-per-page="-1"
            hide-default-footer
            hover
            striped
            density="comfortable"
            class="elevation-1 rounded"
          >
            <template v-slot:[`item.match_winrate`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getWinrateColor(item.match_winrate)}`">{{ item.match_winrate }}%</span>
            </template>
            <template v-slot:[`item.round_winrate`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getWinrateColor(item.round_winrate)}`">{{ item.round_winrate }}%</span>
            </template>
            <template v-slot:[`item.kd_ratio`]="{ item }">
              <v-chip size="small" :color="getRatioColor(item.kd_ratio)" class="font-weight-bold">{{ item.kd_ratio.toFixed(2) }}</v-chip>
            </template>
            <template v-slot:[`item.kills_per_spawn`]="{ item }">
              <span class="font-weight-medium" :class="`text-${getRatioColor(item.kills_per_spawn)}`">{{ item.kills_per_spawn.toFixed(2) }}</span>
            </template>
          </v-data-table>

        </v-card-text>
      </v-card>
    </v-dialog>

  </v-container>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { getAuthToken } from "@/config/api/user.ts";
import { useUserStore } from "@/config/store.ts";

const userStore = useUserStore();
const isLoading = ref(false);
const activeTab = ref('vehicles');
const searchQuery = ref('');

// --- ADVANCED FILTERS ---
const showFilters = ref(false);
const filterBr = ref([0.3, 8.5]);
const filterType = ref(null);
const filterRank = ref(null);
const filterTier = ref(null);
const filterTeam = ref(null);
const availableTeams = ref([]);

const serverItems = ref([]);
const totalItems = ref(0);
const currentOptions = ref({});

const showVehicleDialog = ref(false);
const selectedVehicle = ref(null);
const selectedFilterPlayers = ref([]);
const activeComboStatsList = ref([]);
const isDialogLoading = ref(false);

const showPlayerDialog = ref(false);
const selectedPlayer = ref(null);
const playerVehiclesList = ref([]);
const isPlayerDialogLoading = ref(false);

const isAdmin = computed(() => {
  return userStore.groups.some(group => group.name === 'admin');
});

onMounted(async () => {
  try {
    const res = await fetch(new URL(window.location.origin + '/api/league/teams/slim/'), {
      headers: { 'Content-Type': 'application/json' }
    });
    if (res.ok) {
      availableTeams.value = await res.json();
    }
  } catch (error) {
    console.error("Failed fetching teams:", error);
  }
});

// --- HEADERS ---
const vehicleHeaders = [
  { title: 'Vehicle Name', key: 'name', align: 'start', sortable: true },
  { title: 'Matches', key: 'matches', align: 'center', sortable: true },
  { title: 'Spawns', key: 'spawns', align: 'center', sortable: true },
  { title: 'Match WR', key: 'match_winrate', align: 'center', sortable: true },
  { title: 'Round WR', key: 'round_winrate', align: 'center', sortable: true },
  { title: 'Kills', key: 'kills', align: 'center', sortable: true },
  { title: 'Deaths', key: 'deaths', align: 'center', sortable: true },
  { title: 'K/D Ratio', key: 'kd_ratio', align: 'center', sortable: true },
  { title: 'K/S Ratio', key: 'kills_per_spawn', align: 'center', sortable: true },
];

const allTanksHeaders = [
  { title: 'Vehicle Name', key: 'name', align: 'start', sortable: true },
  { title: 'Usage Rate', key: 'participation_rate', align: 'center', sortable: true },
  { title: 'Matches', key: 'matches', align: 'center', sortable: true },
  { title: 'Spawns', key: 'spawns', align: 'center', sortable: true },
  { title: 'Match WR', key: 'match_winrate', align: 'center', sortable: true },
  { title: 'Round WR', key: 'round_winrate', align: 'center', sortable: true },
  { title: 'Kills', key: 'kills', align: 'center', sortable: true },
  { title: 'Deaths', key: 'deaths', align: 'center', sortable: true },
  { title: 'K/D Ratio', key: 'kd_ratio', align: 'center', sortable: true },
  { title: 'K/S Ratio', key: 'kills_per_spawn', align: 'center', sortable: true },
];

const playerHeaders = [
  { title: 'Player Name', key: 'name', align: 'start', sortable: true },
  { title: 'Matches', key: 'matches', align: 'center', sortable: true },
  { title: 'Spawns', key: 'spawns', align: 'center', sortable: true },
  { title: 'Match WR', key: 'match_winrate', align: 'center', sortable: true },
  { title: 'Round WR', key: 'round_winrate', align: 'center', sortable: true },
  { title: 'Kills', key: 'kills', align: 'center', sortable: true },
  { title: 'Deaths', key: 'deaths', align: 'center', sortable: true },
  { title: 'K/D Ratio', key: 'kd_ratio', align: 'center', sortable: true },
  { title: 'K/S Ratio', key: 'kills_per_spawn', align: 'center', sortable: true },
];

const playerVehiclesHeaders = [
  { title: 'Vehicle', key: 'vehicle', align: 'start', sortable: true },
  { title: 'Matches', key: 'matches', align: 'center', sortable: true },
  { title: 'Spawns', key: 'spawns', align: 'center', sortable: true },
  { title: 'Match WR', key: 'match_winrate', align: 'center', sortable: true },
  { title: 'Round WR', key: 'round_winrate', align: 'center', sortable: true },
  { title: 'Kills', key: 'kills', align: 'center', sortable: true },
  { title: 'Deaths', key: 'deaths', align: 'center', sortable: true },
  { title: 'K/D Ratio', key: 'kd_ratio', align: 'center', sortable: true },
  { title: 'K/S Ratio', key: 'kills_per_spawn', align: 'center', sortable: true },
];

// --- CORE DATA LOADER ---
const loadItems = async (options) => {
  currentOptions.value = options;
  const { page, itemsPerPage, sortBy } = options;

  isLoading.value = true;
  try {
    const url = new URL(window.location.origin + '/api/league/stats/comprehensive/');
    url.searchParams.append('tab', activeTab.value);
    url.searchParams.append('page', page);
    url.searchParams.append('itemsPerPage', itemsPerPage);

    // Filter Attachments
    if (searchQuery.value) url.searchParams.append('search', searchQuery.value);
    if (filterBr.value[0] > 0.3) url.searchParams.append('min_br', filterBr.value[0]);
    if (filterBr.value[1] < 8.5) url.searchParams.append('max_br', filterBr.value[1]);
    if (filterType.value) url.searchParams.append('type', filterType.value);
    if (filterRank.value) url.searchParams.append('rank', filterRank.value);
    if (filterTier.value) url.searchParams.append('tier_context', filterTier.value);
    if (filterTeam.value) url.searchParams.append('team', filterTeam.value);

    if (sortBy && sortBy.length > 0) {
      url.searchParams.append('sortBy', sortBy[0].key);
      url.searchParams.append('sortOrder', sortBy[0].order);
    }

    const headers = { 'Content-Type': 'application/json' };
    if (localStorage.getItem("authToken")) headers['Authorization'] = getAuthToken();

    const response = await fetch(url.toString(), { method: 'GET', headers });
    if (response.ok) {
      const data = await response.json();
      serverItems.value = data.items;
      totalItems.value = data.total;
    }
  } catch (error) {
    console.error("Error fetching stats:", error);
  } finally {
    isLoading.value = false;
  }
};

const forceReload = () => { if (currentOptions.value) loadItems(currentOptions.value); };

// Setup debounced watcher for filters
let filterTimeout;
watch([activeTab, searchQuery, filterBr, filterType, filterRank, filterTier, filterTeam], () => {
  clearTimeout(filterTimeout);
  filterTimeout = setTimeout(() => {
    if (currentOptions.value) {
      currentOptions.value.page = 1;
      loadItems(currentOptions.value);
    }
  }, 500); // 500ms debounce
});

// --- VEHICLE DIALOG LOGIC ---
const openVehicleDetails = (event, { item }) => {
  selectedVehicle.value = item;
  selectedFilterPlayers.value = [];
  activeComboStatsList.value = [];
  showVehicleDialog.value = true;
};

const sortedVehiclePlayers = computed(() => selectedVehicle.value?.players_list || []);

const fetchComboStats = async () => {
  if (!selectedVehicle.value || selectedFilterPlayers.value.length === 0) {
    activeComboStatsList.value = [];
    return;
  }

  isDialogLoading.value = true;
  try {
    const url = new URL(window.location.origin + '/api/league/stats/comprehensive/');
    url.searchParams.append('tab', 'combos');
    url.searchParams.append('vehicle', selectedVehicle.value.name);
    url.searchParams.append('players', selectedFilterPlayers.value.join(','));
    url.searchParams.append('itemsPerPage', -1);
    url.searchParams.append('sortBy', 'kills_per_spawn');
    url.searchParams.append('sortOrder', 'desc');

    const headers = { 'Content-Type': 'application/json' };
    if (localStorage.getItem("authToken")) headers['Authorization'] = getAuthToken();

    const response = await fetch(url.toString(), { method: 'GET', headers });
    if (response.ok) {
      const data = await response.json();
      activeComboStatsList.value = data.items;
    }
  } catch (error) {
    console.error("Error fetching combo stats:", error);
  } finally {
    isDialogLoading.value = false;
  }
};

watch(selectedFilterPlayers, () => fetchComboStats());

const aggregatedComboStats = computed(() => {
  if (activeComboStatsList.value.length === 0) return null;

  const agg = { spawns: 0, kills: 0, deaths: 0, rounds_won: 0, matches: 0, matches_won: 0 };

  activeComboStatsList.value.forEach(stat => {
    agg.spawns += stat.spawns;
    agg.kills += stat.kills;
    agg.deaths += stat.deaths;
    agg.rounds_won += stat.rounds_won;
    agg.matches += stat.matches;
    agg.matches_won += stat.matches_won;
  });

  agg.kd_ratio = agg.deaths > 0 ? agg.kills / agg.deaths : agg.kills;
  agg.kills_per_spawn = agg.spawns > 0 ? agg.kills / agg.spawns : 0;
  agg.round_winrate = agg.spawns > 0 ? (agg.rounds_won / agg.spawns) * 100 : 0;
  agg.match_winrate = agg.matches > 0 ? (agg.matches_won / agg.matches) * 100 : 0;

  return agg;
});

// --- PLAYER DIALOG LOGIC ---
const openPlayerDetails = (event, { item }) => {
  selectedPlayer.value = item;
  playerVehiclesList.value = [];
  showPlayerDialog.value = true;
  fetchPlayerVehicles();
};

const fetchPlayerVehicles = async () => {
  if (!selectedPlayer.value) return;

  isPlayerDialogLoading.value = true;
  try {
    const url = new URL(window.location.origin + '/api/league/stats/comprehensive/');
    url.searchParams.append('tab', 'combos');
    url.searchParams.append('players', selectedPlayer.value.name);
    url.searchParams.append('itemsPerPage', -1);
    url.searchParams.append('sortBy', 'kills_per_spawn');
    url.searchParams.append('sortOrder', 'desc');

    const headers = { 'Content-Type': 'application/json' };
    if (localStorage.getItem("authToken")) headers['Authorization'] = getAuthToken();

    const response = await fetch(url.toString(), { method: 'GET', headers });
    if (response.ok) {
      const data = await response.json();
      playerVehiclesList.value = data.items;
    }
  } catch (error) {
    console.error("Error fetching player's vehicles:", error);
  } finally {
    isPlayerDialogLoading.value = false;
  }
};

// --- UTILS ---
const getRatioColor = (ratio) => {
  if (ratio >= 3.0) return 'purple';
  if (ratio >= 2.0) return 'blue';
  if (ratio >= 1.5) return 'green';
  if (ratio >= 1.0) return 'yellow-darken-3';
  if (ratio >= 0.5) return 'orange-darken-1';
  return 'red';
};

const getWinrateColor = (wr) => {
  if (wr >= 65) return 'purple';
  if (wr >= 55) return 'blue';
  if (wr >= 50) return 'green';
  if (wr >= 45) return 'yellow-darken-3';
  if (wr >= 40) return 'orange-darken-1';
  return 'red';
};
</script>

<style scoped>
.clickable-rows :deep(tbody tr) {
  cursor: pointer;
  transition: background-color 0.2s;
}
</style>