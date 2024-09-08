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
            </v-data-table>
          </v-card-text>
          <v-card-actions>
            <v-btn
              @click="removeSelectedTanks(manufacturer.id)"
              color="error"
              :disabled="!(selectedItems[manufacturer.id] && selectedItems[manufacturer.id].length > 0)"
            >
              Remove Selected Tanks
            </v-btn>
            <v-btn
              @click="openAddTankDialog(manufacturer.id)"
              color="primary"
            >
              Add Tank
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="showAddTankDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="headline">Add New Tank</span>
        </v-card-title>
        <v-card-text>
          <v-form ref="addTankForm">
            <v-select
              v-model="selectedTank"
              :items="tanks"
              item-title="name"
              item-value="id"
              label="Tank Name"
              required
              return-object
              @update:model-value="handleTankSelection"
            ></v-select>

            <v-text-field
              v-model="tankDetails.battle_rating"
              label="Battle Rating"
              readonly
            ></v-text-field>

            <v-text-field
              v-model="tankDetails.price"
              label="Price"
              readonly
            ></v-text-field>

            <v-text-field
              v-model="tankDetails.rank"
              label="Rank"
              readonly
            ></v-text-field>

            <v-text-field
              v-model="tankDetails.type"
              label="Type"
              readonly
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

const $cookies = inject('$cookies');
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
  { text: 'Select', value: 'select' },
  { text: 'Name', value: 'name' },
  { text: 'Battle Rating', value: 'battle_rating' },
  { text: 'Price', value: 'price' },
  { text: 'Rank', value: 'rank' },
  { text: 'Type', value: 'type' },
]);

const selectedItems = ref<Record<number, number[]>>({});
const showAddTankDialog = ref(false);
const currentManufacturerId = ref<number | null>(null);
const tanks = ref<Tank[]>([]);
const selectedTank = ref<Tank | null>(null);

const tankDetails = ref({
  battle_rating: '',
  price: '',
  rank: '',
  type: '',
});

// Handle when a tank is selected
const handleTankSelection = (tank: Tank) => {
  if (tank) {
    tankDetails.value.battle_rating = tank.battle_rating.toFixed(1);
    tankDetails.value.price = tank.price.toString();
    tankDetails.value.rank = tank.rank.toString();
    tankDetails.value.type = tank.type;
  }
};

const fetchManufacturers = async () => {
  try {
    const response = await fetch('/api/league/manufacturers');
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();
    manufacturers.value = data;

    manufacturers.value.forEach((m) => {
      selectedItems.value[m.id] = [];
    });
  } catch (error) {
    console.error('There was a problem with the fetch operation:', error);
  }
};

const addTank = async () => {
  if (!currentManufacturerId.value || !selectedTank.value) {
    return;
  }

  try {
    const response = await fetch(`/api/league/manufacturers/${currentManufacturerId.value}/`, {
      method: 'PATCH',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ add_tank_names: [selectedTank.value.name] }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    showAddTankDialog.value = false;
    await fetchManufacturers();
  } catch (error) {
    console.error('There was a problem with the fetch operation:', error);
  }
};

const removeSelectedTanks = async (manufacturerId: number) => {
  if (!selectedItems.value[manufacturerId] || selectedItems.value[manufacturerId].length === 0) {
    return;
  }

  try {
    const tankNames =
      manufacturers.value
        .find((m) => m.id === manufacturerId)
        ?.tanks.filter((t) => selectedItems.value[manufacturerId].includes(t.id))
        .map((t) => t.name) || [];

    const response = await fetch(`/api/league/manufacturers/${manufacturerId}/`, {
      method: 'PATCH',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ remove_tank_names: tankNames }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    selectedItems.value[manufacturerId] = [];
    await fetchManufacturers();
  } catch (error) {
    console.error('There was a problem with the fetch operation:', error);
  }
};

const openAddTankDialog = (manufacturerId: number) => {
  currentManufacturerId.value = manufacturerId;
  showAddTankDialog.value = true;
};

const fetchTanks = async () => {
  try {
    const response = await fetch('/api/league/tanks/');
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();
    tanks.value = data;
  } catch (error) {
    console.error('Error fetching tanks:', error);
  }
};

// Initialize data on component mount
onMounted(() => {
  fetchManufacturers();
  fetchTanks();
});
</script>