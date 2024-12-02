<template>
  <v-container>
    <v-text-field
      v-model="search"
      label="Search Tanks"
      clearable
      class="mb-6"
    ></v-text-field>
    <p v-if="team.balance">Current Balance: {{ team!.balance.toLocaleString() }} $</p>

    <v-row v-for="manufacturer in filteredManufacturers" :key="manufacturer.id" class="mb-8">
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
                <span>{{ item.price.toLocaleString() }}</span>
              </template>
            </v-data-table>
          </v-card-text>
          <v-card-actions>
            <v-btn v-if="(userStore.groups.some(i => i.name === 'commander') &&
             userStore.team === teamName) || userStore.groups.some(i => i.name === 'admin')"
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

    <v-dialog v-model="successDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Purchase Successful</v-card-title>
        <v-card-text>
          <p>Tanks purchased: </p>
          <ul>
            <li v-for="(tank, index) in purchasedTanks" :key="index">
              {{ tank }}
            </li>
          </ul>
          <p>New Balance: {{ newBalance.toLocaleString() }}$</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="successDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, inject, computed } from 'vue';
import { useRoute } from 'vue-router';
import { getAuthToken } from "../config/api/user.ts";
import { useUserStore } from "../config/store.ts";

const userStore = useUserStore();
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

interface Team {
  name: string;
  balance: number;
}

interface Manufacturer {
  id: number;
  name: string;
  tanks: Tank[];
}

const manufacturers = ref<Manufacturer[]>([]);
const headers = ref([
  { title: '', value: 'select' },
  { title: 'Name', value: 'name', sortable: true },
  { title: 'Battle Rating', value: 'battle_rating', sortable: true },
  { title: 'Price', value: 'price', sortable: true },
  { title: 'Rank', value: 'rank', sortable: true },
  { title: 'Type', value: 'type', sortable: true },
]);

const selectedItems = ref<Record<number, number[]>>({});
const route = useRoute();
const teamName = route.params.TName;

const team = ref<Team>({name: '', balance: 0})
const search = ref(""); // Search term
const successDialog = ref(false);
const purchasedTanks = ref<string[]>([]);
const newBalance = ref<number>(0);

const filteredManufacturers = computed(() => {
  if (!search.value.trim()) {
    return manufacturers.value;
  }

  const searchTerm = search.value.toLowerCase();

  return manufacturers.value.map((manufacturer) => ({
    ...manufacturer,
    tanks: manufacturer.tanks.filter(
      (tank) =>
        tank.name.toLowerCase().includes(searchTerm) ||
        tank.type.toLowerCase().includes(searchTerm) ||
        tank.rank.toString().includes(searchTerm) ||
        tank.battle_rating.toFixed(1).includes(searchTerm)
    ),
  })).filter((manufacturer) => manufacturer.tanks.length > 0);
});

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

    const responseData = await response.json();
    purchasedTanks.value = selectedTankNames;
    newBalance.value = responseData.new_balance;
    team.value.balance = newBalance.value

    selectedItems.value[manufacturerId] = [];
    successDialog.value = true;
  } catch (error) {
    console.error('There was a problem with the purchase operation:', error);
  }
};

const fetchTeamDetails = async () => {
  try {
    const response = await fetch(`/api/league/teams/${teamName}/`);
    if (!response.ok) {
      throw new Error('Error fetching team details');
    }
    team.value = await response.json();
    console.log(team.value)
  } catch (error) {
    console.error('Error fetching team details:', error);
  }
}

onMounted(() => {
  fetchManufacturers();
  fetchTeamDetails()
});

</script>