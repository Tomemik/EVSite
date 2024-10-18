<template>
  <v-container>
    <v-row class="d-flex flex-wrap mt-3">
      <!-- Teams Filter (v-select) -->
      <v-col cols="12" md="3" class="mt-5">
        <v-select
          v-model="settingsStore.filterTeams"
          :items="teamNames"
          label="Filter Teams"
          multiple
          class="align-center"
        ></v-select>
      </v-col>

      <!-- Date Range Picker and Show Played Checkbox -->
      <v-col cols="12" md="6" class="d-flex align-center">
        <div class="d-flex align-center" style="width: 100%;">
          <VueDatePicker v-model="dateFilter" range placeholder="Select a date range to show" style="max-width: 60%" />
          <v-checkbox
            v-model="showPlayed"
            class="d-inline-flex align-start text-no-wrap"
            label="show played"
            style="width: 40%;"
          ></v-checkbox>
        </div>
      </v-col>

      <!-- Apply Filters and Create New Match Button -->
      <v-col cols="12" md="3" class="d-flex align-center justify-end">
        <v-btn color="primary" class="mr-4" @click="fetchMatches">Apply Filters</v-btn>
        <div v-if="userStore.groups.some(i => ['commander', 'admin'].includes(i.name))">
          <v-btn color="primary" @click="openCreateMatchDialog">Create New Match</v-btn>
        </div>
      </v-col>
    </v-row>


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
      @resultView="showResults"
    />

    <MatchResult
      :detailedMatch="detailedMatch"
      :showResultsDialog="showResultsDialog"
      :allTeamDetails="allTeamsDetails"
      @update:showResultsDialog="showResultsDialog = false"
      @postResults="postResults"
      @calcMatch="calcMatch"
    />

    <MatchEdit
      :detailedMatch="detailedMatch"
      :showEditDialog="showEditDialog"
      :allTeamDetails="allTeamsDetails"
      @update:showEditDialog="showEditDialog = $event"
      @updateMatch="updateMatch"
      :isNewMatch="isNewMatch"
    />
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, inject } from 'vue';
import MatchDetails from "../components/MatchDetails.vue";
import MatchEdit from "../components/MatchEdit.vue";
import MatchResult from "../components/MatchResult.vue";
import {useSettingsStore, useUserStore} from "../config/store.ts";
import {getAuthToken} from "../config/api/user.ts";

const $cookies = inject("$cookies");
const csrfToken = $cookies.get('csrftoken');
const userStore = useUserStore()
const settingsStore = useSettingsStore()

const today = ref<Date>(new Date());
const showDetailsDialog = ref(false);
const showEditDialog = ref(false);
const showResultsDialog = ref(false)
const isNewMatch = ref(false);
const matches = ref([]);
const formattedMatches = ref([]);
const detailedMatch = ref();
const allTeamsDetails = ref([])
const teamNames = ref([])
const dateFilter = ref<[Date | null, Date | null] | null>(null);
const showPlayed = ref<boolean>(false)


const toggleEdit = () => {
  showEditDialog.value = true
}

const showResults = () => {
  showResultsDialog.value = true
}

const openCreateMatchDialog = () => {
  detailedMatch.value = {
    id: null,
    datetime: new Date(),
    gamemode: '',
    map_selection: '',
    mode: '',
    best_of_number: 1,
    money_rules: '',
    special_rules: '',
    sides: {
      team_1: [{ team: '', tanks: [] }],
      team_2: [{ team: '', tanks: [] }],
    },
  };
  showEditDialog.value = true;
  isNewMatch.value = true;
};

const fetchMatches = async () => {
  try {
    const params = new URLSearchParams();
    if (settingsStore.filterTeams.length > 0) {
      params.append('team', settingsStore.filterTeams.join(','));
    }
    if (dateFilter.value && dateFilter.value[0]) {
      params.append('from_date', dateFilter.value[0].toISOString());
      if (dateFilter.value[1])
      {
        params.append('to_date', dateFilter.value[1].toISOString());
      }
    }
    params.append('played', String(showPlayed.value))


    const response = await fetch(`/api/league/matches/filtered/?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch matches');
    const data = await response.json();
    console.log(data)
    matches.value = data.results;

    formattedMatches.value = data.results.map((match) => {
      const sides = match.teammatch_set.reduce((acc, tm) => {
        if (!acc[tm.side]) acc[tm.side] = [];
        acc[tm.side].push(tm.team);
        return acc;
      }, {});

      const matchDate = new Date(match.datetime);
      const time = `${matchDate.getUTCHours().toString().padStart(2, '0')}:${matchDate.getUTCMinutes().toString().padStart(2, '0')} UTC`;

      const title = `${Object.values(sides).map(teams => teams.join(' + ')).join(' vs ')} ${time}`;

      return {
        id: match.id,
        title,
        start: matchDate,
        end: new Date(matchDate.getTime() + (60 * 60 * 1000)),
      };
    });
  } catch (error) {
    console.error(error);
  }
};

const fetchMatchDetails = async (match) => {
  try {
    const response = await fetch('/api/league/matches/' + match.id);
    if (!response.ok) throw new Error('Failed to fetch match details');

    const data = await response.json();
    detailedMatch.value = {
      id: data.id,
      datetime: data.datetime,
      gamemode: data.gamemode,
      map_selection: data.map_selection,
      mode: data.mode,
      best_of_number: data.best_of_number,
      money_rules: data.money_rules,
      special_rules: data.special_rules,
      sides: {
        team_1: data.teammatch_set.filter(team => team.side === 'team_1'),
        team_2: data.teammatch_set.filter(team => team.side === 'team_2')
      },
      start: new Date(data.datetime),
      end: new Date(new Date(data.datetime).getTime() + 60 * 60 * 1000)
    };
    console.log(detailedMatch.value)
    showDetailsDialog.value = true;
  } catch (error) {
    console.error('Error fetching match details:', error);
  }
};

const updateMatch = async (updatedMatch) => {
  try {
    const response = await fetch('/api/league/matches/' + (isNewMatch.value ? 'detailed/' : updatedMatch.id + '/'), {
      method: isNewMatch.value ? 'POST' : 'PATCH',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
        'Authorization': getAuthToken(),
      },
      body: JSON.stringify(updatedMatch),
    });
    if (!response.ok) throw new Error('Failed to update match details');
    const data = await response.json();

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
    showEditDialog.value = false;
    isNewMatch.value = false; // Reset the flag
    fetchMatches(); // Refresh match list after creation or update
  } catch (error) {
    console.error('Error updating match:', error);
  }
};

const postResults = async (resultData) => {
  console.log(resultData);
  try {
    const response = await fetch('/api/league/matches/' + resultData.match_id + '/results/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
          'Authorization': getAuthToken(),
        },
        body: JSON.stringify(resultData),
      });
      if (!response.ok) throw new Error('Failed to update match details');
      const data = await response.json();
      console.log(data)
  } catch (error) {
    console.error('Error updating match:', error);
  }
}

const calcMatch = async (id) => {
  try {
    const response = await fetch('/api/league/matches/' + id + '/calc/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
          'Authorization': getAuthToken(),
        },
      });
      if (!response.ok) throw new Error('Failed to update match details');
      const data = await response.json();
      console.log(data)
  } catch (error) {
    console.error('Error updating match:', error);
  }
}

const fetchAllTeams = async () => {
  try {
    const response = await fetch('/api/league/teams/tanks/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) throw new Error('Failed to fetch teams');

    allTeamsDetails.value = await response.json();
    teamNames.value = allTeamsDetails.value.map(item => item.name)
    console.log(teamNames.value)
    console.log(allTeamsDetails.value);

  } catch (error) {
    console.error('Error updating match:', error);
  }
}

onMounted(() => {
  fetchMatches();
  fetchAllTeams()
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