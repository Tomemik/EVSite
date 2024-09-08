<template>
  <v-container>
    <v-calendar
      ref="calendar"
      v-model:now="today"
      type="week"
      :events="formattedMatches"
      :weekdays="[1,2,3,4,5,6,0]"
      color="primary"
      @click:event="showMatchDetails">
      <template #event="{ event }">
        <v-tooltip bottom>
          <template #activator="{ on, attrs }">
            <div
              v-on="on"
              v-bind="attrs"
              @click="showMatchDetails(event)"
              class="event"
            >
              {{ event.title }}
            </div>
          </template>
          <span>{{ event.title }}</span>
        </v-tooltip>
      </template>
    </v-calendar>


    <!-- Match Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="600px">
      <v-card>
        <v-card-title>Match Details</v-card-title>
        <v-card-text v-if="selectedMatch">
          <p><strong>Date:</strong> {{ formatDate(selectedMatch.datetime) }}</p>
          <v-divider></v-divider>
          <div v-for="team in selectedMatch.teammatch_set" :key="team.team.name">
            <p>
              <strong>Team:</strong> {{ team.team.name }} -
              <span :style="{color: team.team.color}">{{ team.team.color }}</span>
              ({{ team.side }})
            </p>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" @click="showDetailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

// Date formatting helper
const formatDate = (datetime: string) => {
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
  };
  return new Date(datetime).toLocaleDateString(undefined, options);
};

const today = ref<Date>(new Date());
const showDetailsDialog = ref(false);
const selectedMatch = ref(null);
const matches = ref([]);
const formattedMatches = ref([]);

// Fetch matches from the backend
const fetchMatches = async () => {
  try {
    const response = await fetch('/api/league/matches/');  // Adjust the endpoint as needed
    if (!response.ok) throw new Error('Failed to fetch matches');
    const data = await response.json();
    matches.value = data;

    console.log(matches.value);

    // Format matches for Vuetify calendar
    formattedMatches.value = data.map((match) => {
      // Group teams by side, but ignore the side label in the output
      const sides = match.teammatch_set.reduce((acc, tm) => {
        if (!acc[tm.side]) {
          acc[tm.side] = [];
        }
        acc[tm.side].push(tm.team.name);
        return acc;
      }, {});

      console.log(sides);

      // Extract the date and time
      const matchDate = new Date(match.datetime);
      const hours = matchDate.getUTCHours().toString().padStart(2, '0');
      const minutes = matchDate.getUTCMinutes().toString().padStart(2, '0');
      const time = `${hours}:${minutes} UTC`;

      // Format the title with teams on the same side grouped together and append time
      const title = Object.values(sides)
        .map(teams => teams.join(' + '))
        .join(' vs ')
        + ` ${time}`;

      console.log(title);

      return {
        title: title,
        start: matchDate,  // Convert to Date object
        end: new Date(matchDate.getTime() + (60*60*1000)),  // Set end time to 1 hour after start
      };
    });

    console.log(formattedMatches.value);
  } catch (error) {
    console.error('Error fetching matches:', error);
  }
};
// Show detailed match info in dialog
const showMatchDetails = (event) => {
  selectedMatch.value = matches.value.find(
    (match) => new Date(match.datetime).getTime() === new Date(event.start).getTime()
  );
  showDetailsDialog.value = true;
};

// Fetch data when the component is mounted
onMounted(() => {
  fetchMatches();
});
</script>

<style scoped>
.event {
  cursor: pointer;
  padding: 4px;
  margin: 2px;
  border-radius: 4px;
  border: solid 1px gray;
  background-color: rgba(0, 0, 255, 0.1);
}
</style>