<template>
  <v-dialog v-model="localShowDetailsDialog" @update:model-value="close" max-width="900px">
    <v-card class="rounded-lg">
      <v-toolbar color="primary" density="compact">
        <v-toolbar-title class="text-subtitle-1 font-weight-bold">
          <v-icon start icon="mdi-calendar-clock"></v-icon>
          {{ detailedMatch ? formatDateTime(detailedMatch.datetime) : 'Match Details' }}
        </v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text v-if="detailedMatch" class="pa-6">

        <v-row class="mb-0" dense>
          <v-col cols="12" md="6">
            <v-list density="compact" nav class="py-0">
              <v-list-item prepend-icon="mdi-controller">
                <v-list-item-subtitle>Game Mode</v-list-item-subtitle>
                <div class="mt-1">
                  <v-chip color="secondary" size="small" class="mr-2" label>
                    {{ getTitleByValue(gamemodeOptions, detailedMatch.gamemode) }}
                  </v-chip>
                  <v-chip variant="outlined" size="small" label>
                    {{ getTitleByValue(modeOptions, detailedMatch.mode) }}
                  </v-chip>
                </div>
              </v-list-item>

              <v-list-item prepend-icon="mdi-trophy-outline">
                <v-list-item-subtitle>Format</v-list-item-subtitle>
                <div class="text-body-2 font-weight-medium">
                  Best of {{ getTitleByValue(bestOfOptions, detailedMatch.best_of_number) }}
                </div>
              </v-list-item>
            </v-list>
          </v-col>

          <v-col cols="12" md="6">
            <v-list density="compact" nav class="py-0">
              <v-list-item prepend-icon="mdi-map-marker">
                <v-list-item-subtitle>Map Selection</v-list-item-subtitle>
                <div class="text-body-2 font-weight-medium">
                  {{ detailedMatch.map_selection }}
                </div>
              </v-list-item>

              <v-list-item prepend-icon="mdi-cash">
                <v-list-item-subtitle>Money Rules</v-list-item-subtitle>
                <div class="text-body-2">
                  {{ getTitleByValue(moneyRulesOptions, detailedMatch.money_rules) }}
                </div>
              </v-list-item>
            </v-list>
          </v-col>
        </v-row>

        <v-row v-if="detailedMatch.special_rules" class="mb-2" dense>
          <v-col cols="12">
            <v-list density="compact" nav class="py-0">
              <v-list-item prepend-icon="mdi-alert-circle-outline">
                <v-list-item-subtitle>Special Rules</v-list-item-subtitle>
                <div class="text-body-2 text-error">
                  {{ detailedMatch.special_rules }}
                </div>
              </v-list-item>
            </v-list>
          </v-col>
        </v-row>

        <v-divider class="mb-6 mt-2"></v-divider>

        <v-row align="stretch">
          <v-col cols="12" md="5">
            <div v-for="team in detailedMatch.sides.team_1" :key="team.team" class="mb-4">
              <v-card variant="outlined" class="h-100 border-grey">
                <v-card-item class="bg-grey-lighten-1 py-2">
                  <div class="text-subtitle-1 font-weight-bold text-center text-primary">
                    {{ team.team }}
                  </div>
                </v-card-item>
                <v-divider></v-divider>
                <v-list density="compact" class="py-0">
                  <v-list-item v-for="tank in team.tanks" :key="tank.id">
                    <template v-slot:prepend>
                      <v-icon icon="mdi-tank" size="small" color="grey"></v-icon>
                    </template>
                    <v-list-item-title>{{ tank.tank.name }}</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-card>
            </div>
          </v-col>

          <v-col cols="12" md="2" class="d-flex justify-center align-center">
            <div class="text-h5 text-disabled font-italic font-weight-black">VS</div>
          </v-col>

          <v-col cols="12" md="5">
            <div v-for="team in detailedMatch.sides.team_2" :key="team.team" class="mb-4">
              <v-card variant="outlined" class="h-100 border-grey">
                <v-card-item class="bg-grey-lighten-1 py-2">
                  <div class="text-subtitle-1 font-weight-bold text-center text-error">
                    {{ team.team }}
                  </div>
                </v-card-item>
                <v-divider></v-divider>
                <v-list density="compact" class="py-0">
                  <v-list-item v-for="tank in team.tanks" :key="tank.id">
                    <template v-slot:prepend>
                      <v-icon icon="mdi-tank" size="small" color="grey"></v-icon>
                    </template>
                    <v-list-item-title class="text-right">{{ tank.tank.name }}</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-card>
            </div>
          </v-col>
        </v-row>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-btn variant="text" color="info" prepend-icon="mdi-content-copy" @click="copyDetails">Copy Discord Format</v-btn>
        <v-btn variant="tonal" color="success" prepend-icon="mdi-scoreboard" @click="openResultView">Result</v-btn>
        <v-spacer></v-spacer>

        <template v-if="userStore.groups.some(i => ['commander', 'judge', 'admin'].includes(i.name))">
          <v-btn color="primary" variant="elevated" prepend-icon="mdi-pencil" @click="toggleEditMode">Edit</v-btn>
          <v-btn color="error" variant="text" prepend-icon="mdi-delete" @click="confirmDelete">Delete</v-btn>
        </template>
        <v-btn variant="plain" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="showDeleteConfirmation" max-width="400px">
    <v-card>
      <v-card-title class="text-h6">Confirm Deletion</v-card-title>
      <v-card-text>
        Are you sure you want to delete this match? This action cannot be undone.
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="error" @click="deleteMatch">Delete</v-btn>
        <v-btn color="primary" @click="showDeleteConfirmation = false">Cancel</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {ref, watch} from 'vue';
import {useUserStore} from "../config/store.ts";

const userStore = useUserStore()

const props = defineProps(['detailedMatch', 'showDetailsDialog']);
const emit = defineEmits(['update:showDetailsDialog', 'deleteMatch', 'editMode', 'resultView']);

const localShowDetailsDialog = ref(props.showDetailsDialog);
const showDeleteConfirmation = ref(false);

watch(() => props.showDetailsDialog, (newValue) => {
  localShowDetailsDialog.value = newValue;
});

const updateShowDetailsDialog = (value) => {
  emit('update:showDetailsDialog', value);
};

const confirmDelete = () => {
  showDeleteConfirmation.value = true;
};

const deleteMatch = () => {
  emit("deleteMatch", props.detailedMatch.id);
  showDeleteConfirmation.value = false;
};

const formatDateTime = (datetime) => {
  const options = {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false
  };
  return new Date(datetime).toLocaleString(undefined, options);
};

const gamemodeOptions = [
  { value: 'annihilation', title: 'Annihilation' },
  { value: 'domination', title: 'Domination' },
  { value: 'flag_tank', title: 'Flag Tank' }
];

const bestOfOptions = [
  { value: '3', title: 'Best of 3' },
  { value: '5', title: 'Best of 5' },
];

const modeOptions = [
  { value: 'traditional', title: 'Traditional' },
  { value: 'advanced', title: 'Advanced' },
  { value: 'evolved', title: 'Evolved' }
];

const moneyRulesOptions = [
  { value: 'money_rule', title: 'Money Rule' },
  { value: 'even_split', title: 'Even Split' },
  { value: 'none', title: 'None' }
];

const getTitleByValue = (options, value) => {
  const option = options.find(opt => opt.value === value);
  return option ? option.title : value;
};

const openResultView = () => {
  emit('resultView');
}

const toggleEditMode = () => {
  emit('editMode');
};

const close = () => {
  updateShowDetailsDialog(false);
}

// ... COPY FUNCTIONALITY (UNCHANGED) ...
const formatDateTimeForCopy = (datetime) => {
  const date = new Date(datetime);

  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const dayName = days[date.getUTCDay()];

  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const monthName = months[date.getUTCMonth()];

  const day = date.getUTCDate();
  const ordinal = (n) => {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return s[(v - 20) % 10] || s[v] || s[0];
  };
  const dayWithOrdinal = `${day}${ordinal(day)}`;

  const year = date.getUTCFullYear();

  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');

  return `${dayName}, ${monthName} ${dayWithOrdinal}, ${year} - ${hours}:${minutes} UTC`;
};

const getDiscordTimestampRelative = (datetime) => {
  const unixTimestamp = Math.floor(new Date(datetime).getTime() / 1000);
  return `<t:${unixTimestamp}:R>`;
};

const getDiscordTimestampFull = (datetime) => {
  const unixTimestamp = Math.floor(new Date(datetime).getTime() / 1000);
  return `<t:${unixTimestamp}:f>`;
};

const copyDetails = () => {
  const matchDetails = `
${formatDateTimeForCopy(props.detailedMatch.datetime)} - ${getDiscordTimestampFull(props.detailedMatch.datetime)} - ${getDiscordTimestampRelative(props.detailedMatch.datetime)}
${getTitleByValue(gamemodeOptions, props.detailedMatch.gamemode)}, ${getTitleByValue(modeOptions, props.detailedMatch.mode)}, Bo${props.detailedMatch.best_of_number}, ${props.detailedMatch.map_selection}
${getTitleByValue(moneyRulesOptions, props.detailedMatch.money_rules)}
${props.detailedMatch.special_rules || 'None'}

${props.detailedMatch.sides.team_1.map(team => `
**${team.team}**:
${team.tanks.map(tank => tank.tank.name).join('\n')}
`).join('')}

--- vs. ---

${props.detailedMatch.sides.team_2.map(team => `
**${team.team}**:
${team.tanks.map(tank => tank.tank.name).join('\n')}
`).join('')}
  `;

  navigator.clipboard.writeText(matchDetails.trim()).then(() => {
    alert('Match details copied to clipboard!');
  }).catch(err => {
    console.error('Failed to copy match details: ', err);
  });
};
</script>


<style scoped>
.border-grey {
  border-color: #BDBDBD !important;
}
</style>