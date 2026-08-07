<template>
  <v-container fluid class="h-100 d-flex flex-column pa-4 bg-background" style="margin: 0 auto;">

    <v-card class="mb-4 elevation-2 flex-shrink-0" shaped>
      <v-card-title class="d-flex justify-space-between align-center primary white--text py-4 bg-primary">
        <div class="d-flex align-center">
          <v-icon start size="x-large" class="mr-3">mdi-poll</v-icon>
          <div>
            <span class="text-h5 font-weight-bold">League Statistics</span>
          </div>
        </div>
        <v-btn color="white" variant="outlined" @click="forceReload" :loading="isLoading">
          <v-icon start>mdi-refresh</v-icon> Refresh Data
        </v-btn>
      </v-card-title>

      <v-toolbar color="surface" density="compact" class="border-b px-2">
        <v-tabs v-model="activeTab" color="primary">
          <v-tab value="general"><v-icon start>mdi-earth</v-icon> General Overview</v-tab>
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

        <div style="width: 350px;" class="my-2" v-if="activeTab !== 'general'">
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
            <!-- New Date Filters -->
            <v-col cols="12" md="2">
              <v-text-field
                v-model="filterStartDate"
                type="date"
                label="Start Date"
                density="compact"
                variant="outlined"
                hide-details
                clearable
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="2">
              <v-text-field
                v-model="filterEndDate"
                type="date"
                label="End Date"
                density="compact"
                variant="outlined"
                hide-details
                clearable
              ></v-text-field>
            </v-col>

            <!-- Quick Date Buttons -->
            <v-col cols="12" md="2" class="d-flex align-center">
              <v-btn-group density="compact" variant="outlined" color="info" divided>
                <v-btn @click="setQuickDate(7)">1W</v-btn>
                <v-btn @click="setQuickDate(30)">1M</v-btn>
              </v-btn-group>
              <v-btn
                icon="mdi-close"
                density="comfortable"
                variant="plain"
                color="error"
                class="ml-1"
                @click="clearDates"
                v-if="filterStartDate || filterEndDate"
                title="Clear Dates"
              ></v-btn>
            </v-col>

            <v-col cols="12" md="2">
              <v-autocomplete
                v-model="filterTeam"
                :items="availableTeams"
                item-title="name"
                item-value="name"
                label="Filter by Team"
                density="compact"
                variant="outlined"
                hide-details
                clearable
              ></v-autocomplete>
            </v-col>

            <!-- Vehicle specific filters (Hidden on General Tab) -->
            <v-col cols="12" md="4" v-if="activeTab !== 'general'">
              <v-row dense>
                <v-col cols="6">
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
                <v-col cols="6">
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
              </v-row>
            </v-col>
          </v-row>
        </v-card>
      </v-expand-transition>
    </v-card>

    <v-card class="flex-grow-1 overflow-hidden elevation-2 d-flex flex-column">
      <v-window v-model="activeTab" class="h-100 overflow-auto">

        <!-- GENERAL TAB -->
        <v-window-item value="general" class="pa-6">
          <div v-if="isLoading" class="d-flex justify-center my-12">
            <v-progress-circular indeterminate size="64" color="primary"></v-progress-circular>
          </div>
          <div v-else-if="generalStats">
            <!-- KPIs -->
            <v-row class="mb-6">
              <v-col cols="12" md="3">
                <v-card color="indigo-darken-4" theme="dark" class="pa-4 elevation-3">
                  <div class="text-caption text-uppercase text-medium-emphasis font-weight-bold">Total Matches Played</div>
                  <div class="text-h4 mt-1 font-weight-bold">{{ generalStats.overview.total_matches }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="3">
                <v-card color="teal-darken-4" theme="dark" class="pa-4 elevation-3">
                  <div class="text-caption text-uppercase text-medium-emphasis font-weight-bold">Rounds Played (uploaded)</div>
                  <div class="text-h4 mt-1 font-weight-bold">{{ generalStats.overview.total_rounds }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="3">
                <v-card color="blue-grey-darken-4" theme="dark" class="pa-4 elevation-3">
                  <div class="text-caption text-uppercase text-medium-emphasis font-weight-bold">Avg Round Length</div>
                  <div class="text-h4 mt-1 font-weight-bold">{{ formatTime(generalStats.overview.avg_round_length_s) }}</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="3">
                <v-card color="green-darken-4" theme="dark" class="pa-4 elevation-3">
                  <div class="text-caption text-uppercase text-medium-emphasis font-weight-bold">Avg Reward / Match</div>
                  <div class="text-h4 mt-1 font-weight-bold text-success">${{ formatNumber(generalStats.overview.avg_reward_per_team) }}</div>
                </v-card>
              </v-col>
            </v-row>

            <v-row>
              <!-- Map Popularity -->
              <v-col cols="12" md="6">
                <v-card class="elevation-2 h-100">
                  <v-card-title class="bg-surface text-subtitle-1 font-weight-bold border-b">
                    <v-icon start>mdi-map</v-icon> Map Popularity
                  </v-card-title>
                  <v-card-text class="pt-4">
                    <div v-for="(data, mapName) in generalStats.maps" :key="mapName" class="mb-3">
                      <!-- Base Map (Clickable) -->
                      <div class="d-flex justify-space-between text-body-2 mb-1 cursor-pointer select-none" @click="toggleMap(mapName)">
                        <span>
                          <v-icon size="small" class="mr-1">
                            {{ expandedMaps[mapName] ? 'mdi-chevron-down' : 'mdi-chevron-right' }}
                          </v-icon>
                          {{ formatMapName(mapName) }}
                        </span>
                        <span class="font-weight-bold">{{ data.total }} rounds</span>
                      </div>

                      <v-progress-linear
                        :model-value="(data.total / generalStats.overview.total_rounds) * 100"
                        color="info"
                        height="8"
                        rounded>
                      </v-progress-linear>

                      <!-- Variant Dropdown -->
                      <v-expand-transition>
                        <div v-if="expandedMaps[mapName]" class="mt-2 pl-6 pr-2 border-s-sm border-info ml-2">
                           <div v-for="(vCount, vName) in data.variants" :key="vName" class="d-flex justify-space-between text-caption text-medium-emphasis mb-1">
                              <span class="text-truncate mr-2">{{ formatMapName(vName) }}</span>
                              <span class="font-weight-bold">{{ vCount }}</span>
                           </div>
                        </div>
                      </v-expand-transition>
                    </div>
                    <div v-if="Object.keys(generalStats.maps).length === 0" class="text-center text-medium-emphasis py-4">No map data available</div>
                  </v-card-text>
                </v-card>
              </v-col>

              <!-- Meta Distributions -->
              <v-col cols="12" md="6" class="d-flex flex-column" style="gap: 16px;">
                <!-- BR Distribution -->
                <v-card class="elevation-2 flex-grow-1">
                  <v-card-title class="bg-surface text-subtitle-1 font-weight-bold border-b">
                    <v-icon start>mdi-chart-bar</v-icon> BR Distribution
                  </v-card-title>
                  <v-card-text class="pt-4">
                    <div v-for="(count, br) in generalStats.br_distribution" :key="br" class="mb-2">
                      <div class="d-flex justify-space-between text-body-2 mb-1">
                        <span>BR {{ br }}</span>
                        <span class="font-weight-bold">{{ count }} spawns</span>
                      </div>
                      <v-progress-linear :model-value="(count / maxDictValue(generalStats.br_distribution)) * 100" color="purple" height="6" rounded></v-progress-linear>
                    </div>
                    <div v-if="Object.keys(generalStats.br_distribution).length === 0" class="text-center text-medium-emphasis py-4">No BR data available</div>
                  </v-card-text>
                </v-card>

                <!-- Class & Gamemode Split -->
                <v-row>
                  <v-col cols="4">
                    <v-card class="elevation-2 h-100">
                      <v-card-title class="bg-surface text-subtitle-1 font-weight-bold border-b text-caption">Modes</v-card-title>
                      <v-card-text class="pt-4">
                        <div v-for="(count, mode) in generalStats.modes" :key="mode" class="mb-2">
                          <div class="d-flex justify-space-between text-caption mb-1">
                            <span class="text-capitalize">{{ mode.replace('_', ' ') }}</span>
                            <span class="font-weight-bold">{{ count }}</span>
                          </div>
                          <v-progress-linear :model-value="(count / maxDictValue(generalStats.modes)) * 100" color="green" height="4"></v-progress-linear>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                  <v-col cols="4">
                    <v-card class="elevation-2 h-100">
                      <v-card-title class="bg-surface text-subtitle-1 font-weight-bold border-b text-caption">Game Modes</v-card-title>
                      <v-card-text class="pt-4">
                        <div v-for="(count, mode) in generalStats.gamemodes" :key="mode" class="mb-2">
                          <div class="d-flex justify-space-between text-caption mb-1">
                            <span class="text-capitalize">{{ mode.replace('_', ' ') }}</span>
                            <span class="font-weight-bold">{{ count }}</span>
                          </div>
                          <v-progress-linear :model-value="(count / maxDictValue(generalStats.gamemodes)) * 100" color="green" height="4"></v-progress-linear>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                  <v-col cols="4">
                    <v-card class="elevation-2 h-100">
                      <v-card-title class="bg-surface text-subtitle-1 font-weight-bold border-b text-caption">Vehicle Classes</v-card-title>
                      <v-card-text class="pt-4">
                        <div v-for="(count, tClass) in generalStats.class_distribution" :key="tClass" class="mb-2">
                          <div class="d-flex justify-space-between text-caption mb-1">
                            <span>{{ tClass }}</span>
                            <span class="font-weight-bold">{{ count }}</span>
                          </div>
                          <v-progress-linear :model-value="(count / maxDictValue(generalStats.class_distribution)) * 100" color="orange" height="4"></v-progress-linear>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-col>
            </v-row>
          </div>
        </v-window-item>

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
const activeTab = ref('general');
const searchQuery = ref('');

// --- ADVANCED FILTERS ---
const showFilters = ref(false);
const filterBr = ref([0.3, 8.5]);
const filterType = ref(null);
const filterRank = ref(null);
const filterTier = ref(null);
const filterTeam = ref(null);
const filterStartDate = ref('');
const filterEndDate = ref('');
const availableTeams = ref([]);

const serverItems = ref([]);
const totalItems = ref(0);
const generalStats = ref(null);
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

const expandedMaps = ref({});

const toggleMap = (name) => {
  expandedMaps.value[name] = !expandedMaps.value[name];
};

const isAdmin = computed(() => {
  return userStore.groups.some(group => group.name === 'admin');
});

// --- QUICK DATE HANDLERS ---
const getLocalDateString = (date) => {
  // Prevents the date from shifting backwards due to UTC timezone offsets
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().split('T')[0];
};

const setQuickDate = (days) => {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - days);

  filterEndDate.value = getLocalDateString(end);
  filterStartDate.value = getLocalDateString(start);
};

const clearDates = () => {
  filterStartDate.value = '';
  filterEndDate.value = '';
};

onMounted(async () => {
  try {
    const res = await fetch(new URL(window.location.origin + '/api/league/teams/'), {
      headers: { 'Content-Type': 'application/json' }
    });
    if (res.ok) {
      availableTeams.value = await res.json();
    }
  } catch (error) {
    console.error("Failed fetching teams:", error);
  }

  if (activeTab.value === 'general') {
    loadItems({ page: 1, itemsPerPage: 25 });
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
  if (options) currentOptions.value = options;
  const page = options?.page || 1;
  const itemsPerPage = options?.itemsPerPage || 25;
  const sortBy = options?.sortBy;

  isLoading.value = true;
  try {
    const url = new URL(window.location.origin + '/api/league/stats/comprehensive/');
    url.searchParams.append('tab', activeTab.value);

    if (activeTab.value !== 'general') {
      url.searchParams.append('page', page);
      url.searchParams.append('itemsPerPage', itemsPerPage);
      if (searchQuery.value) url.searchParams.append('search', searchQuery.value);
      if (filterBr.value[0] > 0.3) url.searchParams.append('min_br', filterBr.value[0]);
      if (filterBr.value[1] < 8.5) url.searchParams.append('max_br', filterBr.value[1]);
      if (filterType.value) url.searchParams.append('type', filterType.value);
      if (filterRank.value) url.searchParams.append('rank', filterRank.value);
      if (filterTier.value) url.searchParams.append('tier_context', filterTier.value);
      if (sortBy && sortBy.length > 0) {
        url.searchParams.append('sortBy', sortBy[0].key);
        url.searchParams.append('sortOrder', sortBy[0].order);
      }
    }

    // Shared filters
    if (filterTeam.value) url.searchParams.append('team', filterTeam.value);
    if (filterStartDate.value) url.searchParams.append('start_date', filterStartDate.value);
    if (filterEndDate.value) url.searchParams.append('end_date', filterEndDate.value);

    const headers = { 'Content-Type': 'application/json' };
    if (localStorage.getItem("authToken")) headers['Authorization'] = getAuthToken();

    const response = await fetch(url.toString(), { method: 'GET', headers });
    if (response.ok) {
      const data = await response.json();

      if (activeTab.value === 'general') {
        generalStats.value = data;
      } else {
        serverItems.value = data.items;
        totalItems.value = data.total;
      }
    }
  } catch (error) {
    console.error("Error fetching stats:", error);
  } finally {
    isLoading.value = false;
  }
};

const forceReload = () => { loadItems(currentOptions.value); };

// Setup debounced watcher for filters
let filterTimeout;
watch([activeTab, searchQuery, filterBr, filterType, filterRank, filterTier, filterTeam, filterStartDate, filterEndDate], () => {
  clearTimeout(filterTimeout);
  filterTimeout = setTimeout(() => {
    if (currentOptions.value) currentOptions.value.page = 1;
    loadItems(currentOptions.value);
  }, 500);
});

// --- FORMATTING UTILS ---
const formatNumber = (num) => {
  if (!num) return '0';
  return Math.round(num).toLocaleString('en-US');
};

const formatTime = (seconds) => {
  if (!seconds) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
};

const formatMapName = (name) => {
  if (!name) return 'Unknown';
  return name.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
};

const maxDictValue = (dict) => {
  const vals = Object.values(dict);
  return vals.length > 0 ? Math.max(...vals) : 1;
};

// --- DIALOG LOGIC ---
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

.cursor-pointer {
  cursor: pointer;
}
.select-none {
  user-select: none;
}
</style>