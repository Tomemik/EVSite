<template>
  <v-dialog v-model="localShowDetailsDialog" @update:model-value="close" max-width="800px">
    <v-card>
      <v-card-title>Match Details</v-card-title>
      <v-card-text v-if="detailedMatch">
        <!-- Date and Time -->
        <p><strong>Date:</strong> {{ formatDateTime(detailedMatch.datetime) }}</p>

        <!-- Basic Match Information -->
        <v-divider></v-divider>
        <p><strong>Mode:</strong> {{ getTitleByValue(modeOptions, detailedMatch.mode) }}</p>
        <p><strong>Game Mode:</strong> {{ getTitleByValue(gamemodeOptions, detailedMatch.gamemode) }}</p>
        <p><strong>Map Selection:</strong> {{ detailedMatch.map_selection }}</p>
        <p><strong>Best of Number:</strong> {{ getTitleByValue(bestOfOptions, detailedMatch.best_of_number) }}</p>
        <p><strong>Special Rules:</strong> {{ detailedMatch.special_rules || 'None' }}</p>
        <p><strong>Money Rules:</strong> {{ getTitleByValue(moneyRulesOptions, detailedMatch.money_rules) }}</p>

        <v-divider></v-divider>

        <v-row>
          <v-col>
            <div v-for="team in detailedMatch.sides.team_1" :key="team.team">
              <p><strong>{{ team.team }}:</strong></p>

              <ul style="list-style-type: none; padding-left: 0;">
                <li v-for="tank in team.tanks" :key="tank.id">{{ tank.tank.name }}</li>
              </ul>
            </div>
          </v-col>

          <v-col class="d-flex justify-center align-center">
            <p style="text-align:center; font-weight: bold;">vs</p>
          </v-col>

          <v-col class="d-flex flex-column align-end">
            <div v-for="team in detailedMatch.sides.team_2" :key="team.team">
              <p><strong>{{ team.team }}:</strong></p>

              <ul style="list-style-type: none; padding-left: 0;">
                <li v-for="tank in team.tanks" :key="tank.id">{{ tank.tank.name }}</li>
              </ul>
            </div>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-btn color="info" @click="copyDetails">Copy Details</v-btn>
        <v-btn color="success" @click="openResultView">Result</v-btn>
        <v-spacer></v-spacer>
        <v-btn v-if="userStore.groups.some(i => ['commander', 'judge', 'admin'].includes(i.name))" color="primary" @click="toggleEditMode">Edit</v-btn>
        <v-btn color="error" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
<script setup>
import {ref, watch} from 'vue';
import {useUserStore} from "../config/store.ts";

const userStore = useUserStore()

const props = defineProps(['detailedMatch', 'showDetailsDialog']);
const emit = defineEmits(['update:showDetailsDialog', 'editMode', 'resultView']);

const localShowDetailsDialog = ref(props.showDetailsDialog);

watch(() => props.showDetailsDialog, (newValue) => {
  localShowDetailsDialog.value = newValue;
});

const updateShowDetailsDialog = (value) => {
  emit('update:showDetailsDialog', value);
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

const getDiscordTimestamp = (datetime) => {
  const unixTimestamp = Math.floor(new Date(datetime).getTime() / 1000);
  return `<t:${unixTimestamp}:R>`;
};

const copyDetails = () => {
  const matchDetails = `
${formatDateTimeForCopy(props.detailedMatch.datetime)} - ${getDiscordTimestamp(props.detailedMatch.datetime)}
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