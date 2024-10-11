<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-sheet>
          <v-row v-for="(school, schoolIndex) in schools" :key="schoolIndex" class="align-center">
            <v-col cols="2" class="grid-cell">
              <v-sheet
                class="pa-0 elevation-1 grid-cell-content"
                :style="{ backgroundColor: school.color }"
                height="100%"
              >
                <div class="school-name">{{ school.school }}</div>
              </v-sheet>
            </v-col>
            <v-col cols="1" class="grid-cell">
              <v-sheet
                class="pa-0 elevation-1 grid-cell-content"
                :style="{ backgroundColor: school.color }"
                height="100%"
              >
                <div class="school-money">{{ school.money }}</div>
              </v-sheet>
            </v-col>

            <v-col cols="9" class="grid-cell">
              <v-row no-gutters>
                <v-col
                  v-for="(log, logIndex) in filteredLogsBySchool(school.school)"
                  :key="logIndex"
                  cols="auto"
                  class="pa-0 log-interactive grid-cell-content"
                  :style="{ backgroundColor: log.color }"
                  @click="openLogDetails(log)"
                >
                  <div class="log-entry">
                    <div class="log-amount">{{ log.amount }}</div>
                    <div class="log-desc">{{ log.details }}</div>
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
          <div><strong>Details:</strong> {{ selectedLog?.details }}</div>
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
import { ref } from 'vue';

interface School {
  school: string;
  money: string;
  color: string;
}

interface Log {
  school: string;
  amount: string;
  description: string;
  details: string;
  color: string;
  date: string;
}

const headers = ref([
  { title: 'Schools', value: 'school' },
  { title: 'Money in Kou', value: 'money' }
]);

const schools = ref<School[]>([
  { school: 'A', money: '243,801', color: '#D1D5DB' },
  { school: 'B', money: '503,045', color: '#92D050' },
  { school: 'B', money: '921,169', color: '#FFC000' },
  { school: 'D', money: '243,801', color: '#D1D5DB' },
  { school: 'E', money: '503,045', color: '#92D050' },
  { school: 'F', money: '921,169', color: '#FFC000' },
    { school: 'G', money: '243,801', color: '#D1D5DB' },
  { school: 'H', money: '503,045', color: '#92D050' },
  { school: 'I', money: '921,169', color: '#FFC000' },
    { school: 'J', money: '243,801', color: '#D1D5DB' },
  { school: 'K', money: '503,045', color: '#92D050' },
  { school: 'L', money: '921,169', color: '#FFC000' },
    { school: 'M', money: '243,801', color: '#D1D5DB' },
  { school: 'N', money: '503,045', color: '#92D050' },
  { school: 'O', money: '921,169', color: '#FFC000' },
    { school: 'P', money: '243,801', color: '#D1D5DB' },
  { school: 'Q', money: '503,045', color: '#92D050' },
  { school: 'R', money: '921,169', color: '#FFC000' },
    { school: 'S', money: '243,801', color: '#D1D5DB' },
  { school: 'T', money: '503,045', color: '#92D050' },
  { school: 'U', money: '921,169', color: '#FFC000' },
    { school: 'V', money: '243,801', color: '#D1D5DB' },
  { school: 'W', money: '503,045', color: '#92D050' },
  { school: 'X', money: '921,169', color: '#FFC000' },
]);

const logs = ref<Log[]>([
  { school: 'A', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
    { school: 'B', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'C', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'D', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'E', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'F', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'G', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'H', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'I', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'J', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'K', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'L', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'M', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'N', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'O', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'P', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'Q', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'R', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'S', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'T', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'U', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'V', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'W', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
  { school: 'X', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },
    { school: 'A', amount: '50000', description: 'Transfer from JSF', details: 'Starting Money', color: '#D1E7DD', date: '2024-10-10' },



]);

function filteredLogsBySchool(schoolName: string) {
  return logs.value.filter(log => log.school === schoolName);
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
</script>

<style scoped>
.grid-cell {
  padding: 0;
  margin: 0;
}

.grid-cell-content {
  border: 1px solid black;
}

.school-name {
  height: 30px;
  font-weight: bold;
  font-size: 1.2rem;
  text-align: center;
}

.school-money {
  height: 30px;
  font-size: 1rem;
  color: #333;
  text-align: center;
}

.log-entry {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  text-align: center;
  height: 30px;
  padding: 1px;
  margin-left: 2px;
  margin-right: 2px;
}

.log-amount {
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: bold;
  font-size: 1rem;
  flex: 1;
}

.log-desc {
  display: flex;
  justify-content: center; /
  align-items: center;
  font-weight: normal;
  font-size: 1rem;
  margin-left: 2px;
  white-space: nowrap;
  flex: 1;
}

.log-description {
  font-style: italic;
}

.log-interactive {
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
}

.log-interactive:hover {
  background-color: rgba(0, 0, 0, 0.1);
}
</style>