<template>
  <v-container>
    <v-row>
      <v-col
        v-for="(group, date) in importGroups"
        :key="date"
        md="2"
      >
        <v-card class="pa-2">
          <v-card-title class="text-center">
            <strong>{{ formattedDate(date) }} - {{ formattedTime(group[0]?.available_from) }}</strong>
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text>
            <v-table dense class="elevation-1">
              <thead>
                <tr>
                  <th class="text-left" style="width: 50%;">Tank</th>
                  <th class="text-right" style="width: 50%;">Your Price</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="tank in group" :key="tank.id">
                  <td>{{ tank.tank_name }}</td>
                  <td class="text-right">{{ calculatePrice(tank) }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import {useUserStore} from "@/config/store.ts";

interface Tank {
  id: number;
  tank_name: string;
  discount: number;
  available_from: string;
  base_discounted_price: number;
}

interface Tank2 {
  id: number,
  name: string,
}

type ImportGroups = Record<string, Tank[]>;

const importGroups = ref<ImportGroups>({});
const userStore = useUserStore()
const teamName = ref(userStore.team);
const allTanks = ref<Tank2[]>([])
const fetchImportGroups = async () => {
  try {
    const response = await fetch("/api/league/imports/grouped/");
    if (!response.ok) throw new Error("Failed to fetch import results.");

    const data: ImportGroups = await response.json();
    importGroups.value = data;
  } catch (error) {
    console.error("Error fetching import results:", error);
  }
};

const fetchManufacturers = async () => {
  try {
    const response = await fetch(`/api/league/manufacturers/?team_name=${teamName.value}`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();
    allTanks.value = data.map(manufacturer => manufacturer.tanks).flat();
    console.log(allTanks.value)

  } catch (error) {
    console.error('There was a problem with the fetch operation:', error);
  }
};

const calculatePrice = (tank) => {
  let tank_price = tank.base_discounted_price;
  const allTank = allTanks.value.find((t) => t.name === tank.tank_name);

  if (allTank) {
    if (tank.battle_rating <= 3.7) {
      tank_price = 0.8 * tank_price;
    } else {
      tank_price = 0.9 * tank_price;
    }
  } else {
    if (tank.battle_rating <= 3.7) {
      tank_price = 1.25 * tank_price;
    } else {
      tank_price = 1.35 * tank_price;
    }
  }

  return tank_price.toLocaleString();
};

const formattedDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const formattedTime = (isoString: string | undefined) => {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toISOString().slice(11, 16) + " UTC";
};

onMounted(() => {
  fetchImportGroups();
  fetchManufacturers()
});
</script>

<style scoped>
.v-table td,
.v-table th {
  font-size: 0.875rem;
  padding: 4px 8px;
}

.v-card {
  max-width: 100%;
}
</style>