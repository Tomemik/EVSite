<template>
  <v-container>
    <v-row v-for="manufacturer in manufacturers" :key="manufacturer.id" class="mb-8">
      <v-col cols="12">
        <v-card>
          <v-card-title>{{ manufacturer.name }}</v-card-title>
          <v-card-text>
            <v-data-table
              :headers="headers"
              :items="manufacturer.tanks"
              item-value="id"
              show-select
              v-model="selectedItems[manufacturer.id]"
              dense
            >
              <template v-slot:[`item.battle_rating`]="{ item }">
                <span>{{ item.battle_rating.toFixed(1) }}</span>
              </template>
              <template v-slot:[`item.price`]="{ item }">
                <span>{{ item.price.toLocaleString() }}$</span>
              </template>
            </v-data-table>
          </v-card-text>
          <v-card-actions>
            <v-btn v-if="userStore.groups.some(i => i.name === 'commander') &&
             userStore.team === teamName) || userStore.groups.some(i => i.name === 'admin'"
              @click="purchaseSelectedTanks(manufacturer.id)"
              color="primary"
              :disabled="!(selectedItems[manufacturer.id] && selectedItems[manufacturer.id].length > 0)"
            >
              Purchase Selected Tanks
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, inject } from 'vue';
import { useRoute } from 'vue-router';
import {getAuthToken} from "../config/api/user.ts";
import {useUserStore} from "../config/store.ts";

const userStore = useUserStore();
const $cookies = inject("$cookies");
const csrfToken = $cookies.get('csrftoken');


interface Tank {
  id: number;
  name: string;
  battle_rating: number;
  price: number;
  rank: number;
  type: string;
}

interface Manufacturer {
  id: number;
  name: string;
  tanks: Tank[];
}

const manufacturers = ref<Manufacturer[]>([]);
const headers = ref([
  { title: 'Select', value: 'select' },
  { title: 'Name', value: 'name' },
  { title: 'Battle Rating', value: 'battle_rating' },
  { title: 'Price', value: 'price' },
  { title: 'Rank', value: 'rank' },
  { title: 'Type', value: 'type' },
]);

const selectedItems = ref<Record<number, number[]>>({});
const route = useRoute();
const teamName = route.params.TName;

const fetchManufacturers = async () => {
  try {
    const response = await fetch(`/api/league/manufacturers/?team_name=${teamName}`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();
    manufacturers.value = data;

    manufacturers.value.forEach(m => {
      selectedItems.value[m.id] = [];
    });
  } catch (error) {
    console.error('There was a problem with the fetch operation:', error);
  }
};

const purchaseSelectedTanks = async (manufacturerId: number) => {
  const selectedTankIds = selectedItems.value[manufacturerId];

  if (!selectedTankIds || selectedTankIds.length === 0) {
    return;
  }

  try {
    const selectedTankNames = manufacturers.value
      .find(m => m.id === manufacturerId)
      ?.tanks.filter(t => selectedTankIds.includes(t.id))
      .map(t => t.name) || [];

    console.log(selectedTankNames)

    const response = await fetch(`/api/league/transactions/buy_tanks/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
        'Authorization': getAuthToken(),
      },
      body: JSON.stringify({ team: teamName, tanks: selectedTankNames }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    selectedItems.value[manufacturerId] = [];
    await fetchManufacturers();
    console.log('Purchase successful!');
  } catch (error) {
    console.error('There was a problem with the purchase operation:', error);
  }
};

// Initialize data on component mount
onMounted(() => {
  fetchManufacturers();
});
</script>