<template>
  <v-container>
    <v-row class="mb-0">
      <v-col cols="12">
        <v-autocomplete
          v-model="selectedSchools"
          :items="schoolNames"
          label="Select Schools to Compare"
          multiple
          dense
          chips
          clearable
        />
      </v-col>
    </v-row>
    <v-row style="margin: 0 0 10px 0">
      <v-col cols="12">
        <v-btn-toggle
          v-model="showTraditional"
          mandatory
          class="d-flex justify-center"
          color="primary"
          dense
        >
          <v-btn :value='true'>Regular Tanks</v-btn>
          <v-btn :value='false'>Traditional Tanks</v-btn>
        </v-btn-toggle>
      </v-col>
    </v-row>

    <v-row style="margin-top: 0">
      <v-col

        v-for="(school, index) in visibleSchools"
        :key="`school-${index}`"
        md="3"
      >
        <v-card class="pa-2">
          <v-card-title :style="{ backgroundColor: school.color }" class="text-center">
            <strong>{{ school.name }}</strong>
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text>
            <v-table
              v-if="showTraditional"
              dense
              class="elevation-1"
            >
              <thead>
                <tr>
                  <th class="text-left" style="width: 50%;">Tank</th>
                  <th class="text-center" style="width: 25%;">BR</th>
                  <th class="text-right" style="width: 25%;">Quantity</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="tank in school.groupedNonTraditionalTanks"
                  :key="tank.id"
                >
                  <td>{{ tank.name }}</td>
                  <td class="text-center">{{ (tank.battleRating).toFixed(1) }}</td>
                  <td class="text-right">{{ tank.quantity }}</td>
                </tr>
              </tbody>
            </v-table>
            <v-table
              v-if="!showTraditional"
              dense
              class="elevation-1"
            >
              <thead>
                <tr style="height: 0;">
                  <th class="text-left" style="width: 50%;">Tank</th>
                  <th class="text-center" style="width: 25%;">BR</th>
                  <th class="text-right" style="width: 25%;">Quantity</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="tank in school.groupedTraditionalTanks"
                  :key="tank.id"
                >
                  <td>{{ tank.name }}</td>
                  <td class="text-center">{{ (tank.battleRating).toFixed(1) }}</td>
                  <td class="text-right">{{ tank.quantity }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row justify="space-between" class="mt-4">
      <v-btn @click="prevPage" :disabled="currentPage === 0" color="primary">
        ← Previous
      </v-btn>
      <v-btn @click="nextPage" :disabled="isLastPage" color="primary">
        Next →
      </v-btn>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";

interface Tank {
  id: number;
  tank_name: string;
  battle_rating: number;
  quantity: number;
}

interface Tank {
  id: number;
  available: boolean;
  is_trad: boolean;
  tank: {
    id: number;
    name: string;
    battle_rating: number;
    rank: number;
    type: string;
    price: number;
  };
}

interface Team {
  id: number;
  name: string;
  color: string;
  balance: number;
  tanks: Tank[];
  groupedTanks: GroupedTank[];
}

interface GroupedTank {
  name: string;
  battleRating: number;
  type: string;
  quantity: number;
}

const showTraditional = ref(true);
const allTeamsDetails = ref([])
const selectedSchools = ref<string[]>([]);
const currentPage = ref(0);
const pageSize = 4;

onMounted(async () => {
  await fetchAllTeams();
});

const groupTanksByTrad = (tanks: Tank[]): { traditional: GroupedTank[]; nonTraditional: GroupedTank[] } => {
  const traditional = [];
  const nonTraditional = [];

  tanks.forEach((currentTank) => {
    const { name, battle_rating, type } = currentTank.tank;
    const targetArray = currentTank.is_trad ? traditional : nonTraditional;

    const existingTank = targetArray.find(
      (t: GroupedTank) =>
        t.name === name && t.battleRating === battle_rating && t.type === type
    );

    if (existingTank) {
      existingTank.quantity += 1;
    } else {
      targetArray.push({
        name,
        battleRating: battle_rating,
        type,
        quantity: 1,
      });
    }
  });

  return { traditional, nonTraditional };
};

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
    //@ts-ignore
    allTeamsDetails.value.forEach((team) => {
      if (team.tanks && Array.isArray(team.tanks)) {
        const grouped = groupTanksByTrad(team.tanks);
        team.groupedTraditionalTanks = grouped.traditional;
        team.groupedNonTraditionalTanks = grouped.nonTraditional;
      }
    });

  } catch (error) {
    console.error('Error updating match:', error);
  }
}

const schoolNames = computed(() => allTeamsDetails.value.map((school) => school.name).sort());

const visibleSchools = computed(() => {
  const filteredSchools = allTeamsDetails.value.filter((school) =>
    selectedSchools.value.includes(school.name)
  );
  const start = currentPage.value * pageSize;
  return filteredSchools.slice(start, start + pageSize);
});

const isLastPage = computed(() => {
  const filteredSchools = allTeamsDetails.value.filter((school) =>
    selectedSchools.value.includes(school.name)
  );
  return (currentPage.value + 1) * pageSize >= filteredSchools.length;
});

const nextPage = () => {
  if (!isLastPage.value) currentPage.value++;
};

const prevPage = () => {
  if (currentPage.value > 0) currentPage.value--;
};

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