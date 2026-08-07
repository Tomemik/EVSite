<template>
  <v-container class="mt-5">
    <v-row justify="space-between" class="mb-2">
      <v-btn @click="prevPage" :disabled="currentPage === 0" color="primary" class="ml-3">
        ← Previous
      </v-btn>
      <v-btn @click="nextPage" :disabled="isLastPage" color="primary" class="mr-3">
        Next →
      </v-btn>
    </v-row>
    <p v-if="team.balance">Current Balance: {{ team.balance.toLocaleString() }} $</p>
    <v-row dense>
      <v-col
        v-for="category in visibleBoxes"
        :key="category.name"
        cols="12"
        sm="6"
        md="4"
      >
        <v-card class="pa-3">
          <v-card-title class="text-center font-weight-bold">
            {{ category.name }}
          </v-card-title>

          <v-card-text>
            <v-divider></v-divider>
            <v-row dense>
              <v-col cols="12" v-for="(tier, index) in category.tiers" :key="index">
                <v-subheader class="text-center font-weight-bold">
                  Tier {{ tier.tier }}
                </v-subheader>
                <v-list dense>
                  <v-list-item
                    v-for="tank in sortedTanks(tier.tanks)"
                    :key="tank.id"
                  >
                    <v-list-item-content>
                      <v-list-item-title>{{ tank.name }}</v-list-item-title>
                      <v-list-item-subtitle>
                        Battle Rating: {{ tank.battle_rating }}
                      </v-list-item-subtitle>
                    </v-list-item-content>
                  </v-list-item>
                </v-list>
                <div class="text-center font-weight-bold mt-2">
                  {{ formatPrice(tier.price) }}
                </div>
                <v-divider></v-divider>

                <div v-if="team.name && canPurchaseBox(tier)" class="text-center">
                  <v-btn
                    v-if="tier.price > team.balance"
                    disabled
                    @click="purchaseBox(tier)"
                    color="primary"
                    class="mx-2"
                    style="width: 150px"
                  >
                    Buy Box
                  </v-btn>
                  <v-btn
                    v-else
                    @click="purchaseBox(tier)"
                    color="primary"
                    class="mx-2"
                    style="width: 150px"
                  >
                    Buy Box
                  </v-btn>

                  <v-btn
                    v-if="tier.price > team.balance"
                    disabled
                    @click="openBox(tier)"
                    color="secondary"
                    class="mx-2"
                    style="width: 150px"
                  >
                    Buy & Open Box
                  </v-btn>
                  <v-btn
                    v-else
                    @click="openBox(tier)"
                    color="secondary"
                    class="mx-2"
                    style="width: 150px"
                  >
                    Buy & Open Box
                  </v-btn>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <LootboxRoulette
      v-model="showRouletteDialog"
      :box-name="boxName"
      :won-tank-name="wonTankName"
      :possible-items="currentBoxContents"
      @claimed="fetchTeamDetails"
    />
  </v-container>
</template>

<script setup>
import {ref, computed, onMounted, inject} from 'vue';
import { useUserStore } from "@/config/store.ts";
import { getAuthToken } from "@/config/api/user.ts";
import LootboxRoulette from "@/components/LootboxRoulette.vue";

const $cookies = inject("$cookies");
const csrfToken = $cookies.get('csrftoken');

const userStore = useUserStore();
const boxes = ref([]);
const team = ref({name: '', balance: 0});
const currentPage = ref(0);
const pageSize = 3;
const showRouletteDialog = ref(false);
const boxName = ref('');
const wonTankName = ref('');

const fetchTankBoxes = async () => {
  try {
    const response = await fetch('/api/league/boxes/');
    boxes.value = await response.json();
  } catch (error) {
    console.error('Error fetching tank boxes:', error);
  }
};

const fetchTeamDetails = async () => {
  try {
    const response = await fetch(`/api/league/teams/${userStore.team}/`);
    if (!response.ok) {
      throw new Error('Error fetching team details');
    }
    team.value = await response.json();
  } catch (error) {
    console.error('Error fetching team details:', error);
  }
};

const groupedBoxes = computed(() => {
  const categories = {};

  // Group boxes by name and retain the is_national flag for sorting later
  for (const box of boxes.value) {
    if (!categories[box.name]) {
      categories[box.name] = {
        name: box.name,
        is_national: box.is_national,
        tiers: []
      };
    }
    categories[box.name].tiers.push(box);
  }

  // Convert object to array and sort tiers inside each category
  const categoriesArray = Object.values(categories).map(category => {
    category.tiers.sort((a, b) => a.tier - b.tier);
    return category;
  });

  // Sort the categories array by the custom priority rules and then alphabetically
  return categoriesArray.sort((a, b) => {
    // Priority logic function
    const getPriority = (category) => {
      if (category.name === team.value.name) return 0; // Highest priority (User's team)
      if (category.is_national) return 1;              // Medium priority (National boxes)
      return 2;                                        // Lowest priority (Other teams' boxes)
    };

    const priorityA = getPriority(a);
    const priorityB = getPriority(b);

    // If priorities are different, sort by priority
    if (priorityA !== priorityB) {
      return priorityA - priorityB;
    }

    // If priorities are the same, sort alphabetically
    return a.name.localeCompare(b.name);
  });
});

const visibleBoxes = computed(() => {
  const start = currentPage.value * pageSize;
  return groupedBoxes.value.slice(start, start + pageSize);
});

const isLastPage = computed(() => {
  return (currentPage.value + 1) * pageSize >= groupedBoxes.value.length;
});

const nextPage = () => {
  if (!isLastPage.value) currentPage.value++;
};

const prevPage = () => {
  if (currentPage.value > 0) currentPage.value--;
};

const sortedTanks = (tanks) => {
  return [...tanks].sort((a, b) => a.battle_rating - b.battle_rating);
};

const formatPrice = (price) => `${price.toLocaleString()}₽`;

// Function to check if a box can be purchased
const canPurchaseBox = (tier) => {
  return tier.is_national || tier.name === team.value.name;
};

// Function to check if a box can be opened
const canOpenBox = (tier) => {
  return tier.is_national || tier.name === team.value.name;
};

const purchaseBox = async (tier) => {
  try {
    const response = await fetch('/api/league/transactions/buy_box/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
        'Authorization': getAuthToken(),
      },
      body: JSON.stringify({
        team: team.value.name,
        box_id: tier.id,
      }),
    });
    const data = await response.json();
    if (response.ok) {
      alert(`Box purchased: ${data.box}`);
      await fetchTeamDetails();
    } else {
      alert('Failed to purchase box.');
    }
  } catch (error) {
    console.error('Error purchasing box:', error);
  }
};

// Add a new ref to hold the contents of the currently selected box
const currentBoxContents = ref([]);

// Update the openBox function:
const openBox = async (tier) => {
  try {
    const response = await fetch('/api/league/transactions/buy_open_box/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
        'Authorization': getAuthToken(),
      },
      body: JSON.stringify({
        team: team.value.name,
        box_id: tier.id,
      }),
    });

    if (response.ok) {
      const wonTank = await response.json();

      // 1. Set the Name
      boxName.value = tier.name;

      // 2. Extract the actual tank names from this specific box
      currentBoxContents.value = tier.tanks.map(t => t.name);

      // 3. Set the winner and trigger the animation
      wonTankName.value = wonTank;
      showRouletteDialog.value = true;
    } else {
      alert('Failed to open box.');
    }
  } catch (error) {
    console.error('Error opening box:', error);
  }
};

onMounted(() => {
  fetchTankBoxes();
  fetchTeamDetails();
});
</script>

<style scoped>
.v-card {
  border: 1px solid #ddd;
  border-radius: 8px;
}

.v-card-title {
  border-bottom: 1px solid #ddd;
  margin-bottom: 8px;
}

.v-list-item {
  padding: 4px 0;
}

.v-subheader {
  margin-top: 8px;
  margin-bottom: 4px;
}

.v-divider {
  margin: 8px 0;
  border-color: #ddd;
}

.v-card-text .text-center {
  margin-top: 8px;
}

.v-btn {
  width: 120px;
}
</style>