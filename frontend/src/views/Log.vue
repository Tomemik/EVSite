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

    <v-row class="logs-table">
      <!-- Sticky Columns -->
      <v-col cols="2" class="sticky-container">
        <v-sheet>
          <v-row
            v-for="(Team, TeamIndex) in teams"
            :key="TeamIndex"
            class="align-center sticky-row"
            style="padding: 0; margin: 0; height: 40px"
          >
            <v-col cols="6" class="grid-cell sticky-col">
              <v-sheet
                class="pa-0 elevation-1 grid-cell-content"
                :style="{ backgroundColor: Team.color }"
                height="100%"
              >
                <div class="Team-name">{{ Team.name }}</div>
              </v-sheet>
            </v-col>

            <v-col cols="6" class="grid-cell sticky-col">
              <v-sheet
                class="pa-0 elevation-1 grid-cell-content"
                :style="{ backgroundColor: Team.color }"
                height="100%"
              >
                <div class="Team-money">{{ Team.balance }}</div>
              </v-sheet>
            </v-col>
          </v-row>
        </v-sheet>
      </v-col>

      <!-- Scrollable Logs -->
      <v-col cols="10" class="scrollable-container">
        <v-sheet>
          <v-row
            v-for="(Team, TeamIndex) in teams"
            :key="TeamIndex"
            class="align-center"
            style="padding: 0; margin: 0; height: 40px"
          >
            <v-col v-if="logs" cols="12" class="grid-cell">
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
  { title: 'Match Reverted', value: 'revert_rewards' },
  { title: 'Tank Bought', value: 'purchase_tank' },
  { title: 'Tank Sold', value: 'sell_tank' },
  { title: 'Tank Upgraded', value: 'upgrade_or_downgrade_tank' },
  { title: 'Money Transfers In', value: 'money_transfer_in' },
  { title: 'Money Transfers Out', value: 'money_transfer_out' },
  { title: 'Imports Purchase', value: 'import_purchase' },
  { title: 'Box Opened', value: 'open_tank_box' },
  { title: 'Box Purchased', value: 'purchase_box' },
];

function filteredLogsByTeam(TeamName: string) {
  //@ts-ignore
  return logs.value
    .filter(log => log.team === TeamName)
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
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
    const data = await response.json();
    teams.value = data.sort((a, b) => a.name.localeCompare(b.name));
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
      'revert_rewards': '#808080',
      'purchase_tank': '#dd7e6b',
      'sell_tank': '#cc4125',
      'upgrade_or_downgrade_tank': '#a64d79',
      'do_direct_upgrade': '#a64d79',
      'money_transfer_in': '#38761d',
      'money_transfer_out': '#38761d',
      'imports_purchase': '#cccccc',
      'open_tank_box': '#46bdc6',
      'purchase_box': '#46bdc6',
    };

    const descMapping: { [key: string]: string } = {
      'calc_rewards': 'Match Reward',
      'revert_rewards': 'Match Reverted',
      'purchase_tank': 'Tank Bought',
      'sell_tank': 'Tank Sold',
      'upgrade_or_downgrade_tank': 'Tank Upgraded',
      'do_direct_upgrade': 'Tank Upgraded',
      'money_transfer_in': 'Transfer In',
      'money_transfer_out': 'Transfer Out',
      'imports_purchase': 'Imports',
      'open_tank_box': 'Box Opened',
      'purchase_box': 'Box Purchased',
    };



    logs.value = data.results.map((log: any) => {
      const amountMatch = log.description.match(/Balance Changed by:\s([+-]?\d+(\.\d+)?)/);
      const amount = amountMatch ? `${parseFloat(amountMatch[1]).toFixed(0)}` : '0';
      let desc = descMapping[log.method_name];

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
        date: new Date(log.timestamp).toLocaleString(),
      } as Log;
    });

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
.logs-table {
  display: flex;
  flex-wrap: nowrap;
  width: 100%;
  overflow-x: hidden;
  padding-left: 10px;
  padding-right: 10px;
}

.sticky-container {
  position: sticky;
  left: 0;
  z-index: 10;
  margin: 0;
  padding: 0;
}

.scrollable-container {
  display: flex;
  flex-wrap: nowrap;
  overflow-x: auto;
  width: 100%;
  padding-top: 15px;
  padding-bottom: 15px;
  margin: 0;
  padding: 0;
}

.grid-cell {
  padding: 0;
  margin: 0;
  box-sizing: border-box;
  height: 100%;
  color: black;
}

.grid-cell-content {
  border: 1px solid black;
  box-sizing: border-box;
  color: black;
}

.Team-name, .Team-money {
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  height: 30px;
  font-weight: bold;
  font-size: 1rem;
}

.Team-money {
  font-weight: bold;
}

.sticky-col {
  position: sticky;
  z-index: 10;
}

.sticky-col:nth-child(1) {
  left: 0;
  z-index: 2;
  width: 80px;
}

.sticky-col:nth-child(2) {
  left: 80px;
  z-index: 2;
  width: 80px;
}

.logs-container {
  display: flex;
  flex-wrap: nowrap;
  overflow-x: auto;
  width: 100%;
  height: 100%;
  padding: 0;
  margin: 0;
  overflow: hidden;
}

.log-entry {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  width: 170px;
  height: 100%;
  padding: 1px;
  margin: 0 2px;
  box-sizing: border-box;
}

.log-amount {
  flex: 1;
  font-weight: bold;
  font-size: 1rem;
}

.log-desc {
  flex: 1;
  font-size: 1rem;
  margin-left: 2px;
  white-space: nowrap;
}

</style>
