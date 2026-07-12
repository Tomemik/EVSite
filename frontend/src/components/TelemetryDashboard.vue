<template>
  <v-container fluid class="flex-grow-1 d-flex flex-column pa-4 overflow-hidden h-100">
    <v-card variant="elevated" class="mb-4 pa-4 flex-shrink-0">
      <v-row dense align="center" class="mb-2">
        <v-col cols="12" md="5">
          <v-select
            v-model="selectedPlayers"
            :items="availablePlayers"
            label="Filter Players"
            multiple
            chips
            closable-chips
            density="compact"
            variant="outlined"
            hide-details
            :disabled="!telemetryData"
          >
            <template v-slot:selection="{ item }">
              <v-chip closable size="small" @click:close="selectedPlayers = selectedPlayers.filter(p => p !== item.raw)">
                <v-icon start size="small" :style="{ color: `hsl(${playerHues[item.raw]}, 100%, 40%)` }">mdi-circle</v-icon>
                {{ item.title }}
              </v-chip>
            </template>
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props">
                <template v-slot:prepend>
                  <v-icon size="small" class="mr-2" :style="{ color: `hsl(${playerHues[item.raw]}, 100%, 40%)` }">mdi-circle</v-icon>
                </template>
                <v-list-item-title>{{ item.title }}</v-list-item-title>
              </v-list-item>
            </template>
          </v-select>
        </v-col>

        <v-col cols="12" md="3">
          <v-select
            v-model="selectedJudges"
            :items="chatSenders"
            label="Select Judges"
            multiple
            chips
            closable-chips
            density="compact"
            variant="outlined"
            hide-details
            clearable
            prepend-inner-icon="mdi-gavel"
            :disabled="!telemetryData"
          ></v-select>
        </v-col>

        <v-col cols="12" md="3">
          <v-select
            v-model="visibleTeams"
            :items="[{title: 'Team 1', value: 'team_1'}, {title: 'Team 2', value: 'team_2'}]"
            label="Show Teams"
            multiple
            chips
            density="compact"
            variant="outlined"
            hide-details
            :disabled="!telemetryData"
          ></v-select>
        </v-col>

        <v-col cols="12" md="1" class="d-flex justify-end align-center">
          <v-btn
            v-if="telemetryData?.replay_files?.length > 0"
            icon="mdi-download"
            variant="tonal"
            color="info"
            class="mr-2"
            @click="downloadReplays"
            v-tooltip="'Download Replays'"
          ></v-btn>
          <v-btn icon="mdi-refresh" variant="tonal" color="primary" @click="resetViewport" v-tooltip="'Reset View'"></v-btn>
        </v-col>
      </v-row>

      <v-row dense align="center">
        <v-col cols="12" md="2">
          <v-text-field
            v-model.number="campingRadius"
            label="Camp Radius (m)"
            type="number"
            density="compact"
            variant="outlined"
            hide-details
            prepend-inner-icon="mdi-radius-outline"
            :disabled="!telemetryData"
          ></v-text-field>
        </v-col>

        <v-col cols="12" md="2">
          <v-text-field
            v-model.number="campingTimeThreshold"
            label="Camp Time (s)"
            type="number"
            density="compact"
            variant="outlined"
            hide-details
            prepend-inner-icon="mdi-clock-outline"
            :disabled="!telemetryData"
          ></v-text-field>
        </v-col>

        <v-col cols="12" md="2">
          <v-text-field
            v-model.number="campingGracePeriod"
            label="Match Start (s)"
            type="number"
            density="compact"
            variant="outlined"
            hide-details
            prepend-inner-icon="mdi-timer-sand"
            v-tooltip="'Ignore the first X seconds of the match'"
            :disabled="!telemetryData"
          ></v-text-field>
        </v-col>

        <v-col cols="12" md="6" class="d-flex flex-wrap justify-space-around px-2">
          <v-checkbox v-model="showZones" label="Zones" density="compact" hide-details :disabled="!telemetryData"></v-checkbox>
          <v-checkbox v-model="showSpawns" label="Spawns" density="compact" hide-details :disabled="!telemetryData"></v-checkbox>
          <v-checkbox v-model="showCrits" label="Crits" density="compact" hide-details :disabled="!telemetryData" color="warning"></v-checkbox>
          <v-checkbox v-model="showKills" label="Kills" density="compact" hide-details :disabled="!telemetryData"></v-checkbox>
          <v-checkbox v-model="showDeaths" label="Deaths" density="compact" hide-details :disabled="!telemetryData"></v-checkbox>
          <v-checkbox v-model="showJudgePings" label="Judge" density="compact" hide-details :disabled="!telemetryData" color="info"></v-checkbox>
        </v-col>
      </v-row>

      <v-row dense align="center" class="mt-3 pt-2 border-top" v-if="telemetryData">
        <v-col cols="auto">
          <v-btn
            :icon="isPlaying ? 'mdi-pause' : 'mdi-play'"
            color="deep-purple-darken-1"
            density="comfortable"
            variant="elevated"
            @click="togglePlayback"
          ></v-btn>
        </v-col>
        <v-col class="px-4">
          <v-slider
            v-model="currentScrubTime"
            :min="minTimelineTime"
            :max="maxTimelineTime"
            :step="1"
            color="deep-purple"
            hide-details
            density="compact"
          ></v-slider>
        </v-col>
        <v-col cols="auto" class="text-caption font-weight-mono text-medium-emphasis">
          {{ formatTime(currentScrubTime) }} / {{ formatTime(maxTimelineTime) }}
        </v-col>
      </v-row>
    </v-card>

    <v-row class="flex-grow-1 overflow-hidden ma-0" style="min-height: 0;">
      <v-col cols="12" md="9" class="h-100 pa-0 pr-2 d-flex flex-column position-relative">
        <v-card class="flex-grow-1 d-flex justify-center align-center overflow-hidden bg-grey-darken-4 rounded position-relative">
          <div v-show="!telemetryData && !isLoadingTelemetry && !isImageLoading" class="text-white text-h6 text-medium-emphasis">
            Select or parse a round to view telemetry.
          </div>

          <v-progress-circular
            v-show="isLoadingTelemetry || isImageLoading"
            indeterminate
            color="primary"
            size="64"
            class="position-absolute"
            style="z-index: 10;"
          ></v-progress-circular>

          <div
            v-show="telemetryData && !isLoadingTelemetry && !isImageLoading"
            class="position-relative d-inline-block"
            :style="{
              lineHeight: 0,
              transform: `translate(${panX}px, ${panY}px) scale(${zoomLevel})`,
              transformOrigin: 'center center',
              transition: isDragging ? 'none' : 'transform 0.1s ease',
              cursor: isDragging ? 'grabbing' : 'grab'
            }"
            @wheel.prevent="handleZoom"
            @mousedown.prevent="startDrag"
            @mousemove.prevent="handleMouseMove"
            @mouseup="endDrag"
            @mouseleave="endDrag"
          >
            <img
              v-if="mapTextureUrl"
              :src="mapTextureUrl"
              alt="Map Grid"
              @load="onMapImageLoaded"
              ref="mapImgRef"
              style="max-width: 100%; max-height: 70vh; display: block; user-select: none; pointer-events: none;"
            />

            <canvas
              ref="telemetryCanvasRef"
              class="position-absolute top-0 left-0 w-100 h-100"
              style="pointer-events: none;"
            ></canvas>
          </div>

          <div class="position-absolute bottom-0 right-0 ma-4 d-flex flex-column gap-2 bg-white rounded elevation-2 pa-1">
            <v-btn icon="mdi-plus" size="small" variant="text" @click="zoomLevel = Math.min(8, zoomLevel + 0.2)" :disabled="!telemetryData"></v-btn>
            <v-btn icon="mdi-minus" size="small" variant="text" @click="zoomLevel = Math.max(0.5, zoomLevel - 0.2)" :disabled="!telemetryData"></v-btn>
          </div>
        </v-card>

        <div
          v-if="tooltip.show"
          class="position-fixed pointer-events-none d-flex flex-column gap-2"
          style="z-index: 9999; transform: translate(-50%, -100%); margin-top: -15px; min-width: 180px;"
          :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
        >
          <div
            v-for="(match, mIdx) in tooltip.matches"
            :key="mIdx"
            class="bg-grey-darken-4 text-white pa-3 rounded elevation-6"
            :style="{ borderLeft: `4px solid ${match.color}` }"
          >
            <div class="font-weight-bold text-body-2 mb-1" :style="{ color: match.color }">
              {{ match.title }}
            </div>
            <div v-for="(line, idx) in match.lines" :key="idx" class="text-caption" style="line-height: 1.2;">
              {{ line }}
            </div>
          </div>
        </div>
      </v-col>

      <v-col cols="12" md="3" class="h-100 pa-0 pl-2">
        <v-card class="h-100 d-flex flex-column border-grey bg-grey-darken-4" theme="dark" variant="outlined">
          <div class="flex-shrink-0">
            <v-tabs v-model="sidebarTab" density="compact" grow bg-color="grey-darken-3">
              <v-tab value="camping">Camping</v-tab>
              <v-tab value="chat">Chat Log</v-tab>
            </v-tabs>
            <v-divider></v-divider>
          </div>

          <div v-if="sidebarTab === 'camping'" class="d-flex flex-column flex-grow-1 overflow-hidden" style="min-height: 0;">
            <div class="pa-2 d-flex justify-space-around bg-grey-darken-3">
              <span class="text-caption">Team 1 Reveals: {{ teamRevealCounts.team_1 }}</span>
              <span class="text-caption">Team 2 Reveals: {{ teamRevealCounts.team_2 }}</span>
            </div>
            <v-list class="pa-0 h-100 overflow-y-auto bg-transparent" v-if="processedCampingLeaderboard.length > 0">
              <v-list-item v-for="player in processedCampingLeaderboard" :key="player.name" class="border-b py-2">
                <v-list-item-title class="font-weight-bold d-flex justify-space-between align-center">
                  <span class="text-truncate">
                    <v-icon size="small" class="mr-1" :style="{ color: `hsl(${playerHues[player.name]}, 100%, 40%)` }">mdi-circle</v-icon>
                    {{ player.name }}
                  </span>
                  <v-chip
                    size="x-small"
                    :color="player.team === 'team_1' ? 'info' : (player.team === 'team_2' ? 'error' : 'grey')"
                    variant="outlined"
                    class="mr-1"
                  >
                    {{ player.team === 'team_1' ? 'Team 1' : (player.team === 'team_2' ? 'Team 2' : 'No Team') }}
                  </v-chip>
                </v-list-item-title>
                <v-list-item-subtitle class="mt-1 d-flex justify-space-between align-center">
                  <span>Total Time: <strong class="text-warning">{{ player.totalCampTime }}s</strong></span>
                  <span class="text-caption text-medium-emphasis">Max: {{ player.longestSingleCamp }}s</span>
                </v-list-item-subtitle>
                <v-list-item-subtitle v-if="player.reveals && player.reveals.length > 0" class="mt-1">
                  <div class="text-purple text-caption font-weight-bold d-flex align-center">
                    <v-icon size="x-small" class="mr-1">mdi-eye-outline</v-icon>
                    Reveals ({{ player.reveals.length }}): {{ player.reveals.map(r => formatTime(r)).join(', ') }}
                  </div>
                </v-list-item-subtitle>
                <v-list-item-subtitle v-if="player.warnings && player.warnings.length > 0" class="mt-1">
                  <div class="text-error text-caption font-weight-bold d-flex align-center">
                    <v-icon size="x-small" class="mr-1">mdi-alert</v-icon>
                    Warned: {{ player.warnings.map(w => formatTime(w)).join(', ') }}
                  </div>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
            <div v-else-if="telemetryData" class="pa-4 text-center text-medium-emphasis text-body-2 d-flex align-center justify-center h-100">
              No camping events detected.
            </div>
          </div>

          <div v-if="sidebarTab === 'chat'" class="d-flex flex-column flex-grow-1 overflow-hidden" style="min-height: 0;">
            <v-list class="pa-0 h-100 overflow-y-auto bg-transparent" v-if="sortedChatLog.length > 0">
              <v-list-item v-for="(msg, idx) in sortedChatLog" :key="idx" class="border-b px-3 py-2" :style="{ opacity: msg.time > currentScrubTime ? 0.35 : 1 }">
                <div class="d-flex justify-space-between align-center mb-1">
                  <span class="font-weight-bold text-caption" :style="{ color: `hsl(${playerHues[msg.sender] || 0}, 100%, 40%)` }">
                    <v-icon size="x-small" class="mr-1">mdi-account</v-icon>
                    {{ msg.sender }}
                  </span>
                  <span class="text-caption text-medium-emphasis">{{ formatTime(msg.time) }}</span>
                </div>
                <div class="text-body-2" style="white-space: pre-wrap; line-height: 1.2;">{{ stripChatTags(msg.text) }}</div>
              </v-list-item>
            </v-list>
            <div v-else class="pa-4 text-center text-medium-emphasis text-body-2 d-flex align-center justify-center h-100">
              No chat messages.
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  telemetryData: {
    type: Object,
    default: null
  },
  isLoadingTelemetry: {
    type: Boolean,
    default: false
  }
});

// Create a computed property to allow transparent use of the passed-in prop
const telemetryData = computed(() => props.telemetryData);

const mapTextureUrl = ref('');
const isImageLoading = ref(false);
const playerHues = ref({});

const currentScrubTime = ref(0);
const minTimelineTime = ref(0);
const maxTimelineTime = ref(0);
const matchStartTime = ref(0);
const isPlaying = ref(false);
let playbackInterval = null;

let currentHitboxes = [];
const tooltip = ref({ show: false, x: 0, y: 0, matches: [] });

const sidebarTab = ref('camping');
const campingRadius = ref(200);
const campingTimeThreshold = ref(90);
const campingGracePeriod = ref(300);

const selectedJudges = ref([]);
const showZones = ref(true);
const showSpawns = ref(true);
const showKills = ref(true);
const showCrits = ref(true);
const showDeaths = ref(true);
const showJudgePings = ref(true);

const zoomLevel = ref(1);
const panX = ref(0);
const panY = ref(0);
const isDragging = ref(false);
const dragStartX = ref(0);
const dragStartY = ref(0);

const selectedPlayers = ref([]);
const visibleTeams = ref(['team_1', 'team_2']);

const mapImgRef = ref(null);
const telemetryCanvasRef = ref(null);

const togglePlayback = () => {
  if (isPlaying.value) {
    stopPlayback();
  } else {
    if (currentScrubTime.value >= maxTimelineTime.value) currentScrubTime.value = minTimelineTime.value;
    isPlaying.value = true;
    playbackInterval = setInterval(() => {
      if (currentScrubTime.value < maxTimelineTime.value) {
        currentScrubTime.value += 1;
      } else {
        stopPlayback();
      }
    }, 100);
  }
};

const stopPlayback = () => {
  isPlaying.value = false;
  if (playbackInterval) {
    clearInterval(playbackInterval);
    playbackInterval = null;
  }
};

const resetViewport = () => { zoomLevel.value = 1; panX.value = 0; panY.value = 0; };

const handleZoom = (e) => {
  if (!telemetryData.value) return;
  const delta = e.deltaY > 0 ? -0.1 : 0.1;
  zoomLevel.value = Math.max(0.5, Math.min(8, zoomLevel.value + delta));
  tooltip.value.show = false;
};

const startDrag = (e) => {
  if (!telemetryData.value) return;
  isDragging.value = true;
  tooltip.value.show = false;
  dragStartX.value = e.clientX - panX.value;
  dragStartY.value = e.clientY - panY.value;
};

const onDrag = (e) => {
  if (!isDragging.value) return;
  panX.value = e.clientX - dragStartX.value;
  panY.value = e.clientY - dragStartY.value;
};

const handleMouseMove = (e) => {
  if (isDragging.value) { onDrag(e); return; }
  if (!telemetryCanvasRef.value || currentHitboxes.length === 0) { tooltip.value.show = false; return; }

  const rect = telemetryCanvasRef.value.getBoundingClientRect();
  const scaleX = telemetryCanvasRef.value.width / rect.width;
  const scaleY = telemetryCanvasRef.value.height / rect.height;
  const mouseX = (e.clientX - rect.left) * scaleX;
  const mouseY = (e.clientY - rect.top) * scaleY;

  const foundMatches = [];
  for (let i = currentHitboxes.length - 1; i >= 0; i--) {
    const hb = currentHitboxes[i];
    if (Math.hypot(hb.x - mouseX, hb.y - mouseY) <= Math.max(hb.r, 8)) foundMatches.push(hb);
  }

  if (foundMatches.length > 0) tooltip.value = { show: true, x: e.clientX, y: e.clientY, matches: foundMatches };
  else tooltip.value.show = false;
};

const endDrag = () => { isDragging.value = false; };

const downloadReplays = () => {
  if (!telemetryData.value?.replay_files) return;

  telemetryData.value.replay_files.forEach(fileUrl => {
    const a = document.createElement('a');
    a.href = fileUrl;
    a.download = fileUrl.split('/').pop() || 'replay.wrpl';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  });
};

const availablePlayers = computed(() => {
  if (!telemetryData.value?.telemetry_data) return [];
  return Object.keys(telemetryData.value.telemetry_data);
});

const sortedChatLog = computed(() => {
  if (!telemetryData.value) return [];
  const rawChat = telemetryData.value.chat || telemetryData.value.chat_log || {};
  const arr = Array.isArray(rawChat) ? rawChat : Object.values(rawChat);

  return [...arr]
    .filter(msg => {
      if (!msg.text) return false;
      const cleanText = stripChatTags(msg.text).trim();
      if (/\[[a-z]\d\]$/i.test(cleanText)) return false;
      return true;
    }).sort((a, b) => a.time - b.time);
});

const stripChatTags = (text) => text ? text.replace(/<[^>]+>/g, '') : "";

const chatSenders = computed(() => [...new Set(sortedChatLog.value.map(c => c.sender))].filter(s => s));

const judgeEvents = computed(() => {
  const events = { warnings: [], reveals: [] };
  if (!selectedJudges.value || selectedJudges.value.length === 0) return events;

  sortedChatLog.value.forEach(msg => {
    if (!selectedJudges.value.includes(msg.sender)) return;
    const stripped = msg.text.toLowerCase().replace(/[^a-z0-9]/g, '');
    if (stripped.includes('mappingwarn') || stripped.includes('locwarn') || stripped.includes('pingwarn')) {
      events.warnings.push(msg.time);
    }
    const revealMatch = msg.text.match(/(?:ping|map|reveal|loc|rev).*?\b([a-z])\s*(\d+)[^0-9]*([1-9])/i);
    if (revealMatch) {
      events.reveals.push({
        time: msg.time,
        row: revealMatch[1].toUpperCase().charCodeAt(0) - 65,
        col: parseInt(revealMatch[2]) - 1,
        numpad: parseInt(revealMatch[3]),
        text: stripChatTags(msg.text)
      });
    }
  });
  return events;
});

watch(visibleTeams, (newTeams, oldTeams) => {
  if (!telemetryData.value || !telemetryData.value.player_spawns) return;
  const spawns = telemetryData.value.player_spawns;
  const removedTeams = oldTeams.filter(t => !newTeams.includes(t));
  const addedTeams = newTeams.filter(t => !oldTeams.includes(t));
  let newSelected = [...selectedPlayers.value];

  removedTeams.forEach(team => {
    const teamPlayers = (spawns[team] || []).map(s => s.player);
    newSelected = newSelected.filter(p => !teamPlayers.includes(p));
  });

  addedTeams.forEach(team => {
    const teamPlayers = (spawns[team] || []).map(s => s.player);
    teamPlayers.forEach(p => {
      if (telemetryData.value.telemetry_data && telemetryData.value.telemetry_data[p] && !newSelected.includes(p)) {
        newSelected.push(p);
      }
    });
  });
  selectedPlayers.value = newSelected;
});

watch(() => props.telemetryData, (data) => {
  if (!data) return;

  if (data.map_details?.texture) {
    isImageLoading.value = true;
    mapTextureUrl.value = `/maps/${data.map_details.texture}`;
  } else {
    isImageLoading.value = false;
    mapTextureUrl.value = '';
  }

  matchStartTime.value = data.start_time_s || 0;
  minTimelineTime.value = 0;
  maxTimelineTime.value = data.end_time_s || 1800;
  currentScrubTime.value = 0;
  campingGracePeriod.value = matchStartTime.value

  const players = Object.keys(data.telemetry_data || {});
  selectedPlayers.value = players;

  playerHues.value = {};
  players.forEach((p, index) => { playerHues.value[p] = Math.floor((index * 137.5) % 360); });

  const detectedJudges = new Set();
  sortedChatLog.value.forEach(msg => {
    const stripped = msg.text.toLowerCase().replace(/[^a-z0-9]/g, '');
    if (stripped.includes('mappingwarn') || stripped.includes('locwarn') || stripped.includes('pingwarn')) {
      detectedJudges.add(msg.sender);
    }
  });
  selectedJudges.value = Array.from(detectedJudges);

  if (!isImageLoading.value) nextTick(() => drawTelemetryMatrix());
}, { immediate: true });

const teamRevealCounts = computed(() => {
  const counts = { team_1: 0, team_2: 0 };
  processedCampingLeaderboard.value.forEach(p => {
    if (counts.hasOwnProperty(p.team)) counts[p.team] += p.reveals.length;
  });
  return counts;
});

const parsedTelemetry = computed(() => {
  if (!telemetryData.value?.telemetry_data) return {};
  const result = {};
  const deathTimes = {};
  Object.values(telemetryData.value.kills || {}).forEach(k => {
    if (!deathTimes[k.victim]) deathTimes[k.victim] = [];
    deathTimes[k.victim].push(parseFloat(k.time_s));
  });
  Object.values(deathTimes).forEach(arr => arr.sort((a, b) => a - b));

  Object.entries(telemetryData.value.telemetry_data).forEach(([player, vehicles]) => {
    result[player] = {};
    const firstDeathTime = (deathTimes[player] && deathTimes[player].length > 0) ? deathTimes[player][0] : Infinity;

    Object.entries(vehicles).forEach(([veh, pointsArray]) => {
      const rawPoints = Array.isArray(pointsArray) ? pointsArray : Object.values(pointsArray);
      const sortedRaw = rawPoints.map(pt => ({ time_s: pt[0] / 1000, x: pt[1], z: pt[2] })).sort((a, b) => a.time_s - b.time_s);
      const sampled = [];
      let lastTime = -999;

      sortedRaw.forEach(pt => {
        if (pt.time_s > firstDeathTime) return;
        if (pt.time_s - lastTime >= 2.0) { sampled.push(pt); lastTime = pt.time_s; }
      });
      result[player][veh] = sampled;
    });
  });
  return result;
});

const isPointInRevealCell = (px, pz, col, row, numpad) => {
  const mapConfig = telemetryData.value.map_details.variant_data;
  const stepX = mapConfig.grid_steps[0];
  const stepZ = mapConfig.grid_steps[1];
  const cellOriginX = mapConfig.grid_zero[0] + (col * stepX);
  const cellOriginZ = mapConfig.grid_zero[1] - (row * stepZ);
  const subWidth = stepX / 3;
  const subHeight = stepZ / 3;
  const subCol = (numpad - 1) % 3;
  const subRow = Math.floor((numpad - 1) / 3);
  const minX = cellOriginX + (subCol * subWidth);
  const maxX = minX + subWidth;
  const maxZ = cellOriginZ - (subRow * subHeight);
  const minZ = maxZ - subHeight;
  const padding = 20;
  return (px >= minX - padding && px <= maxX + padding && pz >= minZ - padding && pz <= maxZ + padding);
};

const processedCampingLeaderboard = computed(() => {
  if (!telemetryData.value || !parsedTelemetry.value) return [];
  const leaderboard = [];
  const telemetry = parsedTelemetry.value;
  const spawns = telemetryData.value.player_spawns || {};
  const reveals = judgeEvents.value.reveals;

  const getPosAtTime = (player, time) => {
    const veh = Object.keys(telemetry[player] || {})[0];
    const pts = telemetry[player]?.[veh] || [];
    const after = pts.find(p => p.time_s >= time);
    const before = [...pts].reverse().find(p => p.time_s <= time);
    if (!before && !after) return null;
    if (!before) return after;
    if (!after) return before;
    const dt = after.time_s - before.time_s;
    if (dt === 0) return before;
    const alpha = (time - before.time_s) / dt;
    return { x: before.x + (after.x - before.x) * alpha, z: before.z + (after.z - before.z) * alpha };
  };

  const killsArr = Object.values(telemetryData.value.kills || {});
  const critsArr = Object.values(telemetryData.value.crits || {});
  const getPlayerTeam = (name) => {
    if (spawns.team_1?.some(s => s.player === name)) return 'team_1';
    if (spawns.team_2?.some(s => s.player === name)) return 'team_2';
    return 'unknown';
  };
  const radiusSq = campingRadius.value * campingRadius.value;

  Object.entries(telemetry).forEach(([playerName, vehicles]) => {
    if (!selectedPlayers.value.includes(playerName)) return;
    const team = getPlayerTeam(playerName);
    if (!visibleTeams.value.includes(team)) return;

    const pResetTimes = [
      ...killsArr.filter(k => k.attacker === playerName).map(k => parseFloat(k.time_s)),
      ...critsArr.filter(c => c.attacker === playerName || c.victim === playerName).map(c => parseFloat(c.time_s))
    ].sort((a, b) => a - b);

    let totalCampTime = 0; let longestSingleCamp = 0; let playerWarnings = [];

    Object.values(vehicles).forEach(ptsArray => {
      const activePts = ptsArray.filter(pt => pt.time_s <= currentScrubTime.value);
      if (activePts.length < 2) return;
      let i = 0;
      while (i < activePts.length) {
        let j = i + 1; let segmentCampTime = 0;
        const nextReset = pResetTimes.find(r => r > activePts[i].time_s);
        const streakLimit = nextReset ? nextReset : Infinity;
        while (j < activePts.length) {
          if (activePts[j].time_s >= streakLimit) { segmentCampTime = streakLimit - activePts[i].time_s; break; }
          const dx = activePts[j].x - activePts[i].x; const dz = activePts[j].z - activePts[i].z;
          if ((dx * dx + dz * dz) <= radiusSq) { segmentCampTime = activePts[j].time_s - activePts[i].time_s; j++; }
          else break;
        }
        const segmentEndTime = activePts[i].time_s + segmentCampTime;
        const effectiveStartTime = Math.max(activePts[i].time_s, campingGracePeriod.value);
        const liveCampDuration = segmentEndTime - effectiveStartTime;

        if (liveCampDuration >= campingTimeThreshold.value) {
          totalCampTime += liveCampDuration;
          if (liveCampDuration > longestSingleCamp) longestSingleCamp = liveCampDuration;
          judgeEvents.value.warnings.forEach(wTime => {
            if (wTime >= effectiveStartTime && wTime <= segmentEndTime && wTime <= currentScrubTime.value) {
              if (!playerWarnings.includes(wTime)) playerWarnings.push(wTime);
            }
          });
        }
        i = j;
      }
    });

    const playerReveals = [];
    reveals.forEach(rev => {
      const pos = getPosAtTime(playerName, rev.time);
      if (pos && isPointInRevealCell(pos.x, pos.z, rev.col, rev.row, rev.numpad)) playerReveals.push(rev.time);
    });

    if (totalCampTime > 0 || playerReveals.length > 0) {
      leaderboard.push({
        name: playerName, team: getPlayerTeam(playerName), totalCampTime: Math.round(totalCampTime),
        longestSingleCamp: Math.round(longestSingleCamp), warnings: playerWarnings.sort((a, b) => a - b), reveals: playerReveals.sort((a, b) => a - b)
      });
    }
  });

  return leaderboard.sort((a, b) => b.totalCampTime - a.totalCampTime);
});

const formatTime = (time_s) => {
  const s = Math.max(0, Math.round(time_s));
  return `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;
};

const getNearestPoint = (playerName, vehicleName, targetTime) => {
  const pData = parsedTelemetry.value[playerName];
  if (!pData) return null;
  let points = pData[vehicleName] || Object.values(pData)[0];
  if (!points) return null;
  const validPoints = points.filter(pt => pt.time_s <= currentScrubTime.value);
  if (validPoints.length === 0) return null;
  let closest = validPoints[0];
  let minDiff = Math.abs(validPoints[0].time_s - targetTime);
  for (let i = 1; i < validPoints.length; i++) {
    let diff = Math.abs(validPoints[i].time_s - targetTime);
    if (diff < minDiff) { minDiff = diff; closest = validPoints[i]; } else break;
  }
  return closest;
};

const drawTelemetryMatrix = () => {
  if (!telemetryData.value || isImageLoading.value) return;
  const canvas = telemetryCanvasRef.value;
  const img = mapImgRef.value;
  if (!canvas || !img || !telemetryData.value?.map_details?.variant_data) return;
  if (img.clientWidth === 0 || img.clientHeight === 0) return;

  if (canvas.width !== img.clientWidth || canvas.height !== img.clientHeight) {
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
  }

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  currentHitboxes = [];

  const mapConfig = telemetryData.value.map_details.variant_data;
  const minX = mapConfig.map_min[0]; const minZ = mapConfig.map_min[1];
  const maxX = mapConfig.map_max[0]; const maxZ = mapConfig.map_max[1];
  const rangeX = (maxX - minX) || 1; const rangeZ = (maxZ - minZ) || 1;
  const toCanvasX = (x) => ((x - minX) / rangeX) * canvas.width;
  const toCanvasY = (z) => ((maxZ - z) / rangeZ) * canvas.height;

  // Grid
  if (mapConfig.grid_zero && mapConfig.grid_size && mapConfig.grid_steps) {
    const cx = toCanvasX(mapConfig.grid_zero[0]); const cy = toCanvasY(mapConfig.grid_zero[1]);
    const cw = (mapConfig.grid_size[0] / rangeX) * canvas.width;
    const ch = (mapConfig.grid_size[1] / rangeZ) * canvas.height;

    ctx.beginPath(); ctx.rect(cx, cy, cw, ch); ctx.strokeStyle = 'rgba(0, 0, 0, 0.8)'; ctx.lineWidth = 2; ctx.stroke();
    const sx = (mapConfig.grid_steps[0] / rangeX) * canvas.width;
    const sz = (mapConfig.grid_steps[1] / rangeZ) * canvas.height;

    if (sx > 0.1 && sz > 0.1) {
      ctx.beginPath(); ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)'; ctx.lineWidth = 1;
      for(let x = cx; x <= cx + cw; x += sx) { ctx.moveTo(x, cy); ctx.lineTo(x, cy + ch); }
      for(let z = cy; z <= cy + ch; z += sz) { ctx.moveTo(cx, z); ctx.lineTo(cx + cw, z); }
      ctx.stroke();

      ctx.font = 'bold 14px "Courier New", Courier, monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      const colCount = Math.round((mapConfig.grid_size[0] / mapConfig.grid_steps[0]));
      const rowCount = Math.round((mapConfig.grid_size[1] / mapConfig.grid_steps[1]));

      for (let i = 0; i < colCount; i++) {
        const num = (i + 1).toString();
        const textX = cx + (i * sx) + (sx / 2); let textY = cy - 12; if (textY < 10) textY = cy + 12;
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.8)'; ctx.lineWidth = 3; ctx.strokeText(num, textX, textY); ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'; ctx.fillText(num, textX, textY);
      }
      for (let i = 0; i < rowCount; i++) {
        let name = ''; let q = i; do { name = String.fromCharCode((q % 26) + 65) + name; q = Math.floor(q / 26) - 1; } while (q >= 0);
        let textX = cx - 12; const textY = cy + (i * sz) + (sz / 2); if (textX < 10) textX = cx + 12;
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.8)'; ctx.lineWidth = 3; ctx.strokeText(name, textX, textY); ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'; ctx.fillText(name, textX, textY);
      }
    }
  }

  // Judge Pings
  if (showJudgePings.value && selectedJudges.value) {
    judgeEvents.value.reveals.forEach(rev => {
      if (rev.time <= currentScrubTime.value) {
        const sx = (mapConfig.grid_steps[0] / rangeX) * canvas.width;
        const sz = (mapConfig.grid_steps[1] / rangeZ) * canvas.height;
        const cx = toCanvasX(mapConfig.grid_zero[0]); const cy = toCanvasY(mapConfig.grid_zero[1]);
        const subRow = Math.floor((9 - rev.numpad) / 3); const subCol = (rev.numpad - 1) % 3;
        const w = sx / 3; const h = sz / 3;
        const startX = cx + (rev.col * sx) + (subCol * w); const startY = cy + (rev.row * sz) + (subRow * h);
        const alpha = (currentScrubTime.value - rev.time) < 15 ? 0.8 : 0.3;

        ctx.fillStyle = `rgba(255, 0, 0, ${alpha})`; ctx.fillRect(startX, startY, w, h);
        ctx.strokeStyle = `rgba(255, 255, 0, ${alpha})`; ctx.lineWidth = 2; ctx.strokeRect(startX, startY, w, h);
        currentHitboxes.push({ x: startX + w/2, y: startY + h/2, r: Math.max(w, h), title: 'Judge Location Reveal', color: '#FFEB3B', lines: [`Grid: ${String.fromCharCode(rev.row + 65)}${rev.col + 1} NUM${rev.numpad}`, `Time: ${formatTime(rev.time)}`, `Raw Log: "${rev.text}"`] });
      }
    });
  }

  // Zones
  if (showZones.value) {
    (telemetryData.value.capture_zones || []).forEach(z => {
      if (!z.tm) return;
      const canvasX = toCanvasX(z.tm[3][0]); const canvasY = toCanvasY(z.tm[3][2]);
      const canvasR = ((Math.hypot(z.tm[0][0], z.tm[0][2]) || 48.0) / rangeX) * canvas.width;
      ctx.beginPath(); ctx.arc(canvasX, canvasY, Math.max(canvasR, 12), 0, 2 * Math.PI);
      ctx.fillStyle = 'rgba(0, 255, 0, 0.3)'; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = '#00FF00'; ctx.stroke();
      currentHitboxes.push({ x: canvasX, y: canvasY, r: Math.max(canvasR, 12), title: z.name || 'Capture Zone', color: '#00FF00', lines: ['Capture zone'] });
    });

    (telemetryData.value.map_areas || []).forEach(area => {
      const tm = area.tm; if (!tm) return;
      const cx = tm[3][0]; const cz = tm[3][2];
      const sx = area.size?.[0] !== undefined ? area.size[0] : Math.abs(tm[0][0]);
      const sz = area.size?.[1] !== undefined ? area.size[1] : Math.abs(tm[2][2]);
      if (sx === 0 || sz === 0) return;
      const flags = area.flags || []; if (flags.includes('65535') || flags.includes('Locked')) return;

      let edgeColor = 'rgba(255, 0, 0, 0.4)'; let labelText = 'Map Boundary';
      if (area.spawn_side === 'team1') { edgeColor = 'rgba(30, 144, 255, 0.4)'; labelText = 'Team 1 Spawn Base'; }
      else if (area.spawn_side === 'team2') { edgeColor = 'rgba(255, 99, 71, 0.4)'; labelText = 'Team 2 Spawn Base'; }
      else if (flags.includes('team1') && flags.includes('team2')) { edgeColor = 'rgba(255, 0, 0, 0.4)'; labelText = 'Restricted Kill Zone'; }

      let vx = [tm[0][0], tm[0][2]]; let vz = [tm[2][0], tm[2][2]];
      const lenX = Math.hypot(vx[0], vx[1]) || 1; const lenZ = Math.hypot(vz[0], vz[1]) || 1;
      vx = [(vx[0]/lenX)*sx, (vx[1]/lenX)*sx]; vz = [(vz[0]/lenZ)*sz, (vz[1]/lenZ)*sz];
      const corners = [[cx - vx[0] - vz[0], cz - vx[1] - vz[1]], [cx + vx[0] - vz[0], cz + vx[1] - vz[1]], [cx + vx[0] + vz[0], cz + vx[1] + vz[1]], [cx - vx[0] + vz[0], cz - vx[1] + vz[1]]];

      ctx.beginPath(); ctx.moveTo(toCanvasX(corners[0][0]), toCanvasY(corners[0][1])); ctx.lineTo(toCanvasX(corners[1][0]), toCanvasY(corners[1][1])); ctx.lineTo(toCanvasX(corners[2][0]), toCanvasY(corners[2][1])); ctx.lineTo(toCanvasX(corners[3][0]), toCanvasY(corners[3][1])); ctx.closePath();
      ctx.fillStyle = edgeColor; ctx.fill();
      const canvasCX = toCanvasX(cx); const canvasCY = toCanvasY(cz);
      ctx.strokeStyle = edgeColor.replace('0.4', '0.8'); ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(canvasCX - 5, canvasCY); ctx.lineTo(canvasCX + 5, canvasCY); ctx.moveTo(canvasCX, canvasCY - 5); ctx.lineTo(canvasCX, canvasCY + 5); ctx.stroke();
      currentHitboxes.push({ x: canvasCX, y: canvasCY, r: (Math.max(sx, sz) / rangeX) * canvas.width, title: labelText, color: edgeColor.replace('0.4', '1.0'), lines: ['Rough spawn area'] });
    });
  }

  // Paths & Camping
  const spawns = telemetryData.value.player_spawns || {};
  const telemetry = parsedTelemetry.value || {};
  const radiusSq = campingRadius.value * campingRadius.value;
  const killsArr = Object.values(telemetryData.value.kills || {});
  const critsArr = Object.values(telemetryData.value.crits || {});
  const segmentsByColor = {};

  Object.entries(telemetry).forEach(([player, vehicles]) => {
    if (!selectedPlayers.value.includes(player)) return;
    const hue = playerHues.value[player] || 0; const pColor = `hsl(${hue}, 100%, 50%)`;
    const pResetTimes = [...killsArr.filter(k => k.attacker === player).map(k => parseFloat(k.time_s)), ...critsArr.filter(c => c.attacker === player || c.victim === player).map(c => parseFloat(c.time_s))].sort((a, b) => a - b);

    Object.entries(vehicles).forEach(([vehName, ptsArray]) => {
      let prettyVehName = vehName; const spawnRecord = (spawns.team_1 || []).concat(spawns.team_2 || []).find(s => s.player === player);
      if (spawnRecord && spawnRecord.vehicle) prettyVehName = spawnRecord.vehicle;

      const points = ptsArray.filter(pt => pt.time_s <= currentScrubTime.value);
      if (points.length === 0) return;

      for (let k = 0; k < points.length - 1; k++) {
        const speed = Math.sqrt(Math.pow(points[k + 1].x - points[k].x, 2) + Math.pow(points[k + 1].z - points[k].z, 2)) / (points[k + 1].time_s - points[k].time_s || 1);
        const pct = Math.max(0, Math.min(1, Math.round((speed / 15.0) * 5) / 5));
        const colorKey = `hsla(${hue}, 100%, ${30 + (pct * 50)}%, ${0.2 + (pct * 0.8)})`;
        if (!segmentsByColor[colorKey]) segmentsByColor[colorKey] = [];
        segmentsByColor[colorKey].push([toCanvasX(points[k].x), toCanvasY(points[k].z), toCanvasX(points[k + 1].x), toCanvasY(points[k + 1].z)]);
      }

      if (showSpawns.value) {
        const startX = toCanvasX(points[0].x); const startY = toCanvasY(points[0].z);
        ctx.fillStyle = pColor; ctx.strokeStyle = '#212121'; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(startX, startY - 8); ctx.lineTo(startX - 8, startY + 6); ctx.lineTo(startX + 8, startY + 6); ctx.closePath(); ctx.fill(); ctx.stroke();
        currentHitboxes.push({ x: startX, y: startY, r: 8, title: 'Player Spawn', color: pColor, lines: [`Player: ${player}`, `Vehicle: ${prettyVehName}`, `Time: ${formatTime(points[0].time_s)}`] });
      }

      const endX = toCanvasX(points[points.length - 1].x); const endY = toCanvasY(points[points.length - 1].z);
      ctx.fillStyle = pColor; ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(endX, endY, 5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      currentHitboxes.push({ x: endX, y: endY, r: 8, title: `Tracker: ${player}`, color: pColor, lines: [`Vehicle: ${prettyVehName}`, `Last Time: ${formatTime(points[points.length - 1].time_s)}`] });

      let i = 0;
      while (i < points.length) {
        let j = i + 1; let segmentCampTime = 0;
        const streakLimit = pResetTimes.find(r => r > points[i].time_s) || Infinity;
        while (j < points.length) {
          if (points[j].time_s >= streakLimit) { segmentCampTime = streakLimit - points[i].time_s; break; }
          if ((Math.pow(points[j].x - points[i].x, 2) + Math.pow(points[j].z - points[i].z, 2)) <= radiusSq) { segmentCampTime = points[j].time_s - points[i].time_s; j++; }
          else break;
        }

        if (segmentCampTime >= campingTimeThreshold.value) {
          const effectiveStartTime = Math.max(points[i].time_s, campingGracePeriod.value);
          const liveCampDuration = (points[i].time_s + segmentCampTime) - effectiveStartTime;
          if (liveCampDuration >= campingTimeThreshold.value) {
            const cx = toCanvasX(points[i].x); const cy = toCanvasY(points[i].z);
            const pixelRadius = (campingRadius.value / rangeX) * canvas.width;
            const hasWarning = judgeEvents.value.warnings.some(w => w >= effectiveStartTime && w <= (points[i].time_s + segmentCampTime) && w <= currentScrubTime.value);

            ctx.beginPath(); ctx.arc(cx, cy, pixelRadius, 0, 2 * Math.PI); ctx.fillStyle = hasWarning ? `rgba(255, 152, 0, 0.4)` : `hsla(${hue}, 90%, 60%, 0.4)`; ctx.fill();
            ctx.lineWidth = hasWarning ? 4 : 2; ctx.strokeStyle = hasWarning ? `#FF5722` : `hsla(${hue}, 100%, 40%, 0.8)`; ctx.stroke();

            const tooltipLines = [`Player: ${player}`, `Duration: ${(liveCampDuration/60).toFixed(1)}m`, `Started: ${formatTime(effectiveStartTime)}`];
            if (hasWarning) tooltipLines.push(`⚠️ WARNING RECEIVED ⚠️`);
            currentHitboxes.push({ x: cx, y: cy, r: pixelRadius, title: 'Camping Zone', color: hasWarning ? '#FF9800' : pColor, lines: tooltipLines });
          }
        }
        i = j;
      }
    });
  });

  ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.lineWidth = 3;
  for (const [color, segments] of Object.entries(segmentsByColor)) {
    ctx.beginPath(); ctx.strokeStyle = color;
    for (let s = 0; s < segments.length; s++) { ctx.moveTo(segments[s][0], segments[s][1]); ctx.lineTo(segments[s][2], segments[s][3]); }
    ctx.stroke();
  }

  // Crits
  if (showCrits.value) {
    Object.values(telemetryData.value.crits || {}).filter(c => parseFloat(c.time_s) <= currentScrubTime.value).forEach(c => {
      if (selectedPlayers.value.includes(c.attacker)) {
        const pt = getNearestPoint(c.attacker, c.attacker_veh, c.time_s);
        if (pt) {
          const cx = toCanvasX(pt.x); const cy = toCanvasY(pt.z);
          ctx.fillStyle = '#FF9800'; ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(cx, cy - 5); ctx.lineTo(cx + 5, cy); ctx.lineTo(cx, cy + 5); ctx.lineTo(cx - 5, cy); ctx.closePath(); ctx.fill(); ctx.stroke();
          currentHitboxes.push({ x: cx, y: cy, r: 6, title: 'Critical Hit Dealt', color: '#FF9800', lines: [`Attacker: ${c.attacker} (${c.attacker_veh})`, `Victim: ${c.victim} (${c.victim_veh})`, `Weapon: ${c.weapon || 'Unknown'}`, `Time: ${formatTime(c.time_s)}`] });
        }
      }
      if (selectedPlayers.value.includes(c.victim)) {
        const pt = getNearestPoint(c.victim, c.victim_veh, c.time_s);
        if (pt) {
          const cx = toCanvasX(pt.x); const cy = toCanvasY(pt.z);
          ctx.strokeStyle = '#FF9800'; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(cx - 4, cy - 4); ctx.lineTo(cx + 4, cy + 4); ctx.moveTo(cx + 4, cy - 4); ctx.lineTo(cx - 4, cy + 4); ctx.stroke();
          currentHitboxes.push({ x: cx, y: cy, r: 6, title: 'Received Critical Damage', color: '#FF9800', lines: [`Victim: ${c.victim} (${c.victim_veh})`, `Damaged by: ${c.attacker} (${c.attacker_veh})`, `Part: ${c.unit_type || 'Unknown'}`, `Time: ${formatTime(c.time_s)}`] });
        }
      }
    });
  }

  // Kills
  Object.values(telemetryData.value.kills || {}).filter(k => parseFloat(k.time_s) <= currentScrubTime.value).forEach(k => {
    if (showKills.value && selectedPlayers.value.includes(k.attacker)) {
      const pt = getNearestPoint(k.attacker, k.attacker_veh, k.time_s);
      if (pt) {
        const cx = toCanvasX(pt.x); const cy = toCanvasY(pt.z);
        ctx.fillStyle = `hsl(${playerHues.value[k.attacker] || 0}, 100%, 50%)`; ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(cx, cy - 8); ctx.lineTo(cx + 8, cy); ctx.lineTo(cx, cy + 8); ctx.lineTo(cx - 8, cy); ctx.closePath(); ctx.fill(); ctx.stroke();
        currentHitboxes.push({ x: cx, y: cy, r: 10, title: 'Kill Secured', color: `hsl(${playerHues.value[k.attacker] || 0}, 100%, 50%)`, lines: [`Attacker: ${k.attacker} (${k.attacker_veh})`, `Victim: ${k.victim} (${k.victim_veh})`, `Weapon: ${k.weapon}`, `Time: ${formatTime(k.time_s)}`] });
      }
    }
    if (showDeaths.value && selectedPlayers.value.includes(k.victim)) {
      const pt = getNearestPoint(k.victim, k.victim_veh, k.time_s);
      if (pt) {
        const cx = toCanvasX(pt.x); const cy = toCanvasY(pt.z);
        ctx.strokeStyle = `hsl(${playerHues.value[k.victim] || 0}, 100%, 40%)`; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(cx - 6, cy - 6); ctx.lineTo(cx + 6, cy + 6); ctx.moveTo(cx + 6, cy - 6); ctx.lineTo(cx - 6, cy + 6); ctx.stroke();
        currentHitboxes.push({ x: cx, y: cy, r: 10, title: 'Player Died', color: `hsl(${playerHues.value[k.victim] || 0}, 100%, 40%)`, lines: [`Victim: ${k.victim} (${k.victim_veh})`, `Killed by: ${k.attacker} (${k.attacker_veh})`, `Time: ${formatTime(k.time_s)}`] });
      }
    }
  });
};

const onMapImageLoaded = () => { isImageLoading.value = false; drawTelemetryMatrix(); };

watch([currentScrubTime, selectedJudges, selectedPlayers, campingRadius, campingTimeThreshold, campingGracePeriod, showZones, showSpawns, showKills, showCrits, showDeaths, showJudgePings], () => {
  if (telemetryData.value && !isImageLoading.value) drawTelemetryMatrix();
});

let resizeTimeout;
const handleResize = () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => { if (telemetryData.value && !isImageLoading.value) drawTelemetryMatrix(); }, 100);
};

onMounted(() => { window.addEventListener('resize', handleResize); });
onUnmounted(() => { window.removeEventListener('resize', handleResize); clearTimeout(resizeTimeout); stopPlayback(); });
</script>

<style scoped>
.gap-2 { gap: 8px; }
.border-top { border-top: 1px solid #E0E0E0; }
.pointer-events-none { pointer-events: none; }
</style>