<template>
  <v-container>
    <v-calendar
      ref="calendar"
      v-model:now="today"
      type="week"
      :events="formattedMatches"
      :weekdays="[1,2,3,4,5,6,0]"
      color="primary">
      <template #event="{ event }">
        <v-tooltip bottom>
          <template #activator="{ attrs }">
            <div
              v-bind="attrs"
              @click="fetchMatchDetails(event)"
              class="event"
            >
              {{ event.title }}
            </div>
          </template>
          <span>{{ event.title }}</span>
        </v-tooltip>
      </template>
    </v-calendar>

    <MatchDetails
      :detailedMatch="detailedMatch"
      :showDetailsDialog="showDetailsDialog"
      @update:showDetailsDialog="showDetailsDialog = false"
      @editMode="toggleEdit"
    />

    <MatchEdit
      :detailedMatch="detailedMatch"
      :showEditDialog="showEditDialog"
      @update:showEditDialog="showEditDialog = $event"
      @updateMatch="updateMatch"
    />
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MatchDetails from "../components/MatchDetails.vue";
import MatchEdit from "../components/MatchEdit.vue";

const toggleEdit = () => {
  showEditDialog.value = true
  console.log(showEditDialog.value)
}

const formatDate = (datetime: string) => {
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
  };
  return new Date(datetime).toLocaleDateString(undefined, options);
};

const formatTime = (datetime: string) => {
  const date = new Date(datetime);
  return date.toLocaleTimeString();
}

const today = ref<Date>(new Date());
const showDetailsDialog = ref(false);
const showEditDialog = ref(false)
const matches = ref([]);
const formattedMatches = ref([]);
const detailedMatch = ref()

const fetchMatches = async () => {
  try {
    const response = await fetch('/api/league/matches/');
    if (!response.ok) throw new Error('Failed to fetch matches');
    const data = await response.json();
    matches.value = data;


    formattedMatches.value = data.map((match) => {
      const sides = match.teammatch_set.reduce((acc, tm) => {
        if (!acc[tm.side]) {
          acc[tm.side] = [];
        }
        acc[tm.side].push(tm.team.name);
        return acc;
      }, {});

      const matchDate = new Date(match.datetime);
      const hours = matchDate.getUTCHours().toString().padStart(2, '0');
      const minutes = matchDate.getUTCMinutes().toString().padStart(2, '0');
      const time = `${hours}:${minutes} UTC`;

      const title = Object.values(sides)
        .map(teams => teams.join(' + '))
        .join(' vs ')
        + ` ${time}`;


      return {
        id: match.id,
        title: title,
        start: matchDate,
        end: new Date(matchDate.getTime() + (60*60*1000)),
      };
    });

  } catch (error) {
  }
};

const fetchMatchDetails = async (match) => {
  try {
    const response = await fetch('/api/league/matches/' + match.id);
    if (!response.ok) throw new Error('Failed to fetch match details');

    const data = await response.json();

    // Process the detailed match data and group teams by sides
    detailedMatch.value = {
      best_of_number: data.best_of_number,
      datetime: data.datetime,
      gamemode: data.gamemode,
      id: data.id,
      map_selection: data.map_selection,
      mode: data.mode,
      money_rules: data.money_rules,
      special_rules: data.special_rules,
      sides: {
        team_1: data.teammatch_set.filter(team => team.side === 'team_1'),
        team_2: data.teammatch_set.filter(team => team.side === 'team_2')
      },
      start: new Date(data.datetime),
      end: new Date(new Date(data.datetime).getTime() + 60 * 60 * 1000)
    };
    showDetailsDialog.value = true;
    console.log(detailedMatch.value)
  } catch (error) {
    console.error('Error fetching match details:', error);
  }
};

const updateMatch = async (updatedMatch) => {
  console.log(updatedMatch)
}

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