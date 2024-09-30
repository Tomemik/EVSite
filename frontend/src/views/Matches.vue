<template>
  <v-container>
    <div v-if="userStore.groups.some(i => ['commander', 'admin'].includes(i.name))" class="d-flex justify-end mb-3">
      <v-btn color="primary" @click="openCreateMatchDialog">Create New Match</v-btn>
    </div>

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
import {useUserStore} from "../config/store.ts";
import {getAuthToken} from "../config/api/user.ts";

const $cookies = inject("$cookies");
const csrfToken = $cookies.get('csrftoken');
const userStore = useUserStore()

const today = ref<Date>(new Date());
const showDetailsDialog = ref(false);
const showEditDialog = ref(false);
const showResultsDialog = ref(false)
const isNewMatch = ref(false);
const matches = ref([]);
const formattedMatches = ref([]);
const detailedMatch = ref();
const allTeamsDetails = ref([])

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
    const response = await fetch('/api/league/matches/');
    if (!response.ok) throw new Error('Failed to fetch matches');
    const data = await response.json();
    matches.value = data;

    formattedMatches.value = data.map((match) => {
      const sides = match.teammatch_set.reduce((acc, tm) => {
        if (!acc[tm.side]) acc[tm.side] = [];
        acc[tm.side].push(tm.team.name);
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

const fetchAllTeams = async () => {
  try {
    const response = await fetch('/api/league/teams/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) throw new Error('Failed to fetch teams');

    const teams = await response.json();
    const teamNames = teams.map(team => team.name);

    const teamDetailsPromises = teamNames.map(async (teamName) => {
      const teamResponse = await fetch(`/api/league/teams/${teamName}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!teamResponse.ok) throw new Error(`Failed to fetch details for team: ${teamName}`);

      const teamData = await teamResponse.json();

      return teamData;
    });

    allTeamsDetails.value = await Promise.all(teamDetailsPromises);
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