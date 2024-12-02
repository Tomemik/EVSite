<template>
  <v-container>
    <v-row>
      <v-col cols="3">
        <label>Types:</label>
        <v-select
          v-model="selectedMethods"
          :items="methodOptions"
          label="Filter Logs"
          multiple
        ></v-select>
      </v-col>
      <v-col cols="6">
        <label>Date range:</label>
        <VueDatePicker v-model="dateFilter" range />
      </v-col>
      <v-col cols="3">
        <v-btn color="primary" @click="fetchLogs">Apply Filters</v-btn>
      </v-col>
    </v-row>

    <div class="scrollable-container">
      <v-row>
        <v-col cols="12">
          <v-sheet>
            <v-row v-for="(Team, TeamIndex) in teams" :key="TeamIndex" class="align-center">
              <v-col cols="2" class="grid-cell sticky-col">
                <v-sheet
                  class="pa-0 elevation-1 grid-cell-content"
                  :style="{ backgroundColor: Team.color }"
                  height="100%"
                >
                  <div class="Team-name">{{ Team.name }}</div>
                </v-sheet>
              </v-col>

              <v-col cols="1" class="grid-cell sticky-col">
                <v-sheet
                  class="pa-0 elevation-1 grid-cell-content"
                  :style="{ backgroundColor: Team.color }"
                  height="100%"
                >
                  <div class="Team-money">{{ Team.balance }}</div>
                </v-sheet>
              </v-col>

              <v-col v-if="logs" cols="9" class="grid-cell">
                <v-row no-gutters class="logs-container">
                  <v-col
                    v-for="(log, logIndex) in filteredLogsByTeam(Team.name)"
                    :key="logIndex"
                    cols="auto"
                    class="pa-0 log-interactive grid-cell-content"
                    :style="{ backgroundColor: log.color }"
                    @click="openLogDetails(log)"
                  >
                    <div class="log-entry">
                      <div class="log-amount">{{ log.amount }}</div>
                      <div class="log-desc">{{ log.description }}</div>
                    </div>
                  </v-col>
                </v-row>
              </v-col>
            </v-row>
          </v-sheet>
        </v-col>
      </v-row>
    </div>

    <v-dialog v-model="isDialogOpen" max-width="500px">
      <v-card>
        <v-card-title>Log Details</v-card-title>
        <v-card-text>
          <div><strong>Amount:</strong> {{ selectedLog?.amount }}</div>
          <div><strong>Description:</strong> {{ selectedLog?.description }}</div>
          <div><strong>Details:</strong> <span v-html="selectedLog?.full_details"></span></div>
          <div><strong>Date:</strong> {{ selectedLog?.date }}</div>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" @click="closeLogDetails">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import {onMounted, ref} from 'vue';

interface Team {
  name: string;
  balance: string;
  color: string;
}

interface Log {
  team: string;
  amount: string;
  description: string;
  full_details: string;
  color: string;
  date: string;
}

const teams = ref<Team[]>();
const logs = ref<Log[]>();
const selectedMethods = ref<any[]>([]);
const dateFilter = ref<[Date | null, Date | null] | null>(null);
const methodOptions = [
  { title: 'Match Reward', value: 'calc_rewards' },
  { title: 'Tank Bought', value: 'purchase_tank' },
  { title: 'Tank Sold', value: 'sell_tank' },
  { title: 'Tank Upgraded', value: 'upgrade_or_downgrade_tank' },
];

function filteredLogsByTeam(TeamName: string) {
  //@ts-ignore
  return logs.value.filter(log => log.team === TeamName);
}

const isDialogOpen = ref(false);
const selectedLog = ref<Log | null>(null);

function openLogDetails(log: Log) {
  selectedLog.value = log;
  isDialogOpen.value = true;
}

function closeLogDetails() {
  isDialogOpen.value = false;
  selectedLog.value = null;
}

const fetchTeams = async () => {
  try {
    const response = await fetch('/api/league/teams/');
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    teams.value = await response.json();
    console.log(teams.value)
  } catch (error) {
    console.error('Error fetching teams:', error);
  }
};

const fetchLogs = async () => {
  try {
    const params = new URLSearchParams();
    if (selectedMethods.value.length > 0) {
      selectedMethods.value.forEach(method => {
        params.append('method_name', method);
      });
    }
    if (dateFilter.value && dateFilter.value[0] && dateFilter.value[1]) {
      params.append('from_date', dateFilter.value[0].toISOString());
      params.append('to_date', dateFilter.value[1].toISOString());
    }

    const response = await fetch(`/api/league/transactions/money_log/?${params.toString()}`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();

    const colorMapping: { [key: string]: string } = {
      'calc_rewards': '#9fc5e8',
      'purchase_tank': '#dd7e6b',
      'sell_tank': '#cc4125',
      'upgrade_or_downgrade_tank': '#a64d79',
    };

    const descMapping: { [key: string]: string } = {
      'calc_rewards': 'Match Reward',
      'purchase_tank': 'Tank Bought',
      'sell_tank': 'Tank Sold',
      'upgrade_or_downgrade_tank': 'Tank Upgraded',
    };



    logs.value = data.results.map((log: any) => {
      const amountMatch = log.description.match(/Balance Changed by:\s([+-]?\d+(\.\d+)?)/);
      const amount = amountMatch ? `${parseFloat(amountMatch[1]).toFixed(0)}` : 'N/A';
      let desc = descMapping[log.method_name];
      console.log(desc)

      console.log(log.description)
        if (desc === 'Tank Bought') {
          const addedMatch = log.description.match(/Added Tanks:\s*(.*)/);
          const addedTanks = addedMatch ? addedMatch[1].replace(/\*\*/g, '').trim() : 'N/A';
          desc = addedTanks
        } else if (desc === 'Tank Sold') {
          const removedMatch = log.description.match(/Removed Tanks:\s*(.*)/);
          const removedTanks = removedMatch ? removedMatch[1].replace(/\*\*/g, '').trim() : 'N/A';
          desc = removedTanks
        } else if (desc === 'Tank Upgraded') {
          const addedMatch = log.description.match(/Added Tanks:\s*(.*)/);
          const addedTanks = addedMatch ? addedMatch[1].replace(/\*\*/g, '').trim() : 'N/A';

          const removedMatch = log.description.match(/Removed Tanks:\s*(.*)/);
          const removedTanks = removedMatch ? removedMatch[1].replace(/\*\*/g, '').trim() : 'N/A';

          desc = removedTanks + ' -> ' + addedTanks;
      }

      return {
        team: log.team_name,
        amount: amount,
        description: descMapping[log.method_name],
        full_details: log.description.replace(/\n/g, '<br>'),
        color: colorMapping[log.method_name] || '#FFFFFF',
        date: new Date(log.timestamp).toLocaleDateString(),
      } as Log;
    });

    console.log(logs.value);
  } catch (error) {
    console.error('Error fetching logs:', error);
  }
};

onMounted(() => {
  fetchTeams();
  fetchLogs();
});
</script>

<style scoped>
.grid-cell {
  padding: 0;
  margin: 0;
}

.grid-cell-content {
  border: 1px solid black;
}

.Team-name {
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  height: 30px;
  font-weight: bold;
  font-size: 1rem;
  text-align: center;
}

.Team-money {
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  height: 30px;
  font-size: 1rem;
  font-weight: bold;
  text-align: center;
}

.log-entry {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  text-align: center;
  height: 30px;
  width: 170px;
  padding: 1px;
  margin-left: 2px;
  margin-right: 2px;
}

.log-amount {
  display: flex;
  justify-content: left;
  align-items: center;
  font-weight: bold;
  font-size: 1rem;
  flex: 1;
}

.log-desc {
  display: flex;
  justify-content: right;
  align-items: center;
  font-weight: normal;
  font-size: 1rem;
  margin-left: 2px;
  white-space: nowrap;
  flex: 1;
}


.log-interactive {
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
}

.log-interactive:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.scrollable-container {
  display: flex;
  flex-wrap: nowrap;
  overflow-x: auto;
  width: 100%;
  padding: 15px;
}



.logs-container {
  padding-left: 8px;
  display: flex;
  flex-wrap: nowrap;
}

.sticky-col {
  position: -webkit-sticky;
  position: sticky;
  z-index: 1;
  background-color: white;
}

.sticky-col:nth-child(1) {
  left: 0;
  z-index: 2;
}

.sticky-col:nth-child(2) {
  left: calc(2 * (100% / 12));
  z-index: 2;
}

.grid-cell-content {
  color: black;
}

.log-entry {
  color: black;
}

</style>
