<template>
  <v-container :height="'90vh'">
    <TankTable :tanks="tanks"></TankTable>

    <v-dialog v-model="showAddTankDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="headline">Add New Tank</span>
        </v-card-title>
        <v-card-text>
          <v-form ref="addTankForm">
            <v-text-field
              v-model="newTankName"
              label="Tank Name"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTankBattleRating"
              label="Battle Rating"
              type="number"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTankPrice"
              label="Price"
              type="number"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTankRank"
              label="Rank"
              type="number"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTankType"
              label="Type"
              required
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="addTank">Add Tank</v-btn>
          <v-btn @click="showAddTankDialog = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, inject } from 'vue';
import TankTable from "../components/TankTable.vue";

const $cookies = inject("$cookies");
//@ts-ignore
const csrfToken = $cookies.get('csrftoken');

interface Tank {
  id: number;
  name: string;
  battle_rating: number;
  price: number;
  rank: number;
  type: string;
}

const tanks = ref<Tank[]>([]);
const showAddTankDialog = ref(false);
const newTankName = ref('');
const newTankBattleRating = ref<number | null>(null);
const newTankPrice = ref<number | null>(null);
const newTankRank = ref<number | null>(null);
const newTankType = ref('');

const fetchTanks = async () => {
  try {
    const response = await fetch('/api/league/tanks/');
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();
    tanks.value = data;

    localStorage.setItem('tanks', JSON.stringify(data));
    localStorage.setItem('tanksTimestamp', Date.now().toString());
  } catch (error) {
    console.error('There was a problem with the fetch operation:', error);
  }
};

const addTank = async () => {
  if (
    !newTankName.value.trim() ||
    newTankBattleRating.value === null ||
    newTankPrice.value === null ||
    newTankRank.value === null ||
    !newTankType.value.trim()
  ) {
    return;
  }

  try {
    const response = await fetch('/api/league/tanks/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: newTankName.value.trim(),
        battle_rating: newTankBattleRating.value,
        price: newTankPrice.value,
        rank: newTankRank.value,
        type: newTankType.value.trim(),
      }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    // Clear form fields
    newTankName.value = '';
    newTankBattleRating.value = null;
    newTankPrice.value = null;
    newTankRank.value = null;
    newTankType.value = '';

    showAddTankDialog.value = false;

    // Fetch fresh data and update the cache
    await fetchTanks();
  } catch (error) {
    console.error('There was a problem with the fetch operation:', error);
  }
};

onMounted(async () => {
  const cachedData = localStorage.getItem('tanks');
  const cacheTimestamp = localStorage.getItem('tanksTimestamp');
  const now = Date.now();

  if (cachedData && cacheTimestamp && now - parseInt(cacheTimestamp, 10) < 15 * 60 * 1000) {
    tanks.value = JSON.parse(cachedData);
  } else {
    await fetchTanks();
  }
});
</script>