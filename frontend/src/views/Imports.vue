<template>
  <v-container>
    <p v-if="team.balance">Current Balance: {{ team!.balance.toLocaleString() }} $</p>
    <v-row>
      <v-col
        v-for="(group, index) in visibleGroups"
        :key="`group-${index}`"
        cols="12"
        md="3"
      >
        <v-card class="pa-2 h-100">
          <v-card-title class="text-center text-wrap py-3">
            <div class="text-h6 font-weight-bold mb-1">
              {{ formattedDate(group.date) }}
            </div>
            <div class="text-subtitle-3 text-medium-emphasis font-weight-bold">
              {{ formattedTimeUTC(group.tanks[0]?.available_from) }}
            </div>
            <div class="text-subtitle-1 text-disabled">
              {{ formattedTimeLocal(group.tanks[0]?.available_from) }}
            </div>
          </v-card-title>

          <v-divider></v-divider>

          <v-card-text class="px-2">
            <v-table dense class="elevation-1">
              <thead>
                <tr>
                  <th class="text-left" style="width: 45%;">Tank</th>
                  <th class="text-right" style="width: 35%;">Your Price</th>
                  <th class="text-center" style="width: 20%;">Action</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="tank in group.tanks"
                  :key="tank.id"
                  :class="{
                    'purchased-tank': isPurchased(tank),
                    'expired-tank': isExpired(tank) && !isPurchased(tank)
                  }"
                >
                  <td class="text-body-2 font-weight-medium">
                    <span :class="{ 'text-line-through': isPurchased(tank) }">
                      {{ tank.tank_name }}
                    </span>
                  </td>
                  <td class="text-right text-body-2">
                    <span :class="{ 'text-line-through': isPurchased(tank) }">
                      {{ calculatePrice(tank).toLocaleString() }}
                    </span>
                  </td>
                  <td class="text-center pa-1">
                    <v-btn
                      color="success"
                      size="large"
                      @click="initiatePurchase(tank)"
                      class="mt-1"
                      :disabled="!isCommander || isPurchased(tank) || isExpired(tank) || isBeforeAvailableFrom(tank) || !canAfford(tank)"
                    >
                      Buy
                    </v-btn>
                  </td>
                </tr>
              </tbody>
            </v-table>
            <v-btn
              color="primary"
              block
              class="mt-4"
              @click="viewCriteria(group.criteria)"
            >
              View Criteria
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row justify="space-between" class="mb-2 mt-4">
      <v-btn @click="prevPage" :disabled="currentPage === 0" color="primary" class="ml-3">
        ← Previous
      </v-btn>
      <v-btn @click="nextPage" :disabled="isLastPage" color="primary" class="mr-3">
        Next →
      </v-btn>
    </v-row>

    <v-dialog v-model="showCriteriaDialog" max-width="500px">
      <v-card>
        <v-card-title class="text-h6">Offer Criteria</v-card-title>
        <v-divider></v-divider>
        <v-card-text v-if="currentCriteria">
          <p><strong>Name:</strong> {{ currentCriteria.name }}</p>
          <p><strong>Min Rank:</strong> {{ currentCriteria.min_rank || "N/A" }}</p>
          <p><strong>Max Rank:</strong> {{ currentCriteria.max_rank || "N/A" }}</p>
          <p><strong>Tank Type:</strong> {{ currentCriteria.tank_type || "N/A" }}</p>
          <p><strong>Discount:</strong> {{ currentCriteria.discount }}%</p>
          <div>
            <p>
              <strong>Required Tanks:</strong>
            </p>
            <div v-for="(tank) in visibleTanks" :key="tank.id">
              <p>- {{ tank.name }}</p>
            </div>

            <v-expand-transition>
              <div v-show="isExpanded">
                <div v-for="(tank) in hiddenTanks" :key="`hidden-${tank.id}`">
                  <p>- {{ tank.name }}</p>
                </div>
              </div>
            </v-expand-transition>

            <v-btn
              v-if="visibleTanks.length + hiddenTanks.length >= maxVisibleTanks"
              color="primary"
              @click="isExpanded = !isExpanded"
              small
            >
              {{ isExpanded ? "Show Less" : "Show More" }}
            </v-btn>
          </div>
          <p>
            <strong>Required Tank Discount:</strong> {{ currentCriteria.required_tank_discount }}%
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showCriteriaDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showCaptchaDialog" max-width="400px" persistent>
      <v-card>
        <v-card-title class="text-h6">Verify Purchase</v-card-title>
        <v-divider></v-divider>
        <v-card-text>
          <p class="mb-4">To prevent auto-clickers, please solve this quick math problem to confirm your purchase of <strong>{{ targetTank?.tank_name }}</strong>.</p>
          <p class="text-h5 text-center font-weight-bold mb-4">{{ num1 }} + {{ num2 }} = ?</p>
          <v-text-field
            v-model="captchaInput"
            label="Your Answer"
            type="number"
            variant="outlined"
            density="compact"
            autofocus
            @keyup.enter="verifyAndPurchase"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="error" variant="text" @click="showCaptchaDialog = false">Cancel</v-btn>
          <v-btn
            color="success"
            variant="elevated"
            :disabled="captchaInput !== expectedAnswer"
            @click="verifyAndPurchase"
          >
            Confirm
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, inject } from "vue";
import { useUserStore } from "@/config/store.ts";
import { getAuthToken } from "@/config/api/user.ts";

const $cookies = inject("$cookies");
//@ts-ignore
const csrfToken = $cookies.get('csrftoken');

// ... (Your existing interfaces remain exactly the same) ...
interface Tank {
  id: number;
  name: string;
  tank_name: string;
  discount: number;
  available_from: string;
  available_until: string;
  base_discounted_price: number;
  battle_rating: number;
  is_purchased: boolean;
}

interface Criteria {
  name: string;
  min_rank: number | null;
  max_rank: number | null;
  tank_type: string | null;
  discount: number;
  required_tank_discount: number;
  required_tanks : [{ id: number; name: string}];
}

interface Group {
  date: string;
  criteria: Criteria | null;
  tanks: Tank[];
}

interface Team {
  name: string;
  balance: number;
}

type ImportGroups = Record<string, Group>;

const team = ref<Team>({name: '', balance: 0})
const currentPage = ref(0);
const pageSize = 4;
const importGroups = ref<ImportGroups>({});
const userStore = useUserStore();
const teamName = ref(userStore.team);
const allTanks = ref<Tank[]>([]);

const showCriteriaDialog = ref(false);
const currentCriteria = ref<Criteria | null>(null);
const currentTime = ref(Date.now());
let timeInterval: ReturnType<typeof setInterval>;

const isExpanded = ref(false);
const maxVisibleTanks = 3;

// --- CAPTCHA STATE ---
const showCaptchaDialog = ref(false);
const targetTank = ref<Tank | null>(null);
const num1 = ref(0);
const num2 = ref(0);
const captchaInput = ref("");

const expectedAnswer = computed(() => (num1.value + num2.value).toString());

const initiatePurchase = (tank: Tank) => {
  targetTank.value = tank;
  num1.value = Math.floor(Math.random() * 20) + 1;
  num2.value = Math.floor(Math.random() * 20) + 1;
  captchaInput.value = "";
  showCaptchaDialog.value = true;
};

const verifyAndPurchase = () => {
  if (captchaInput.value === expectedAnswer.value && targetTank.value) {
    purchaseTank(targetTank.value);
    showCaptchaDialog.value = false;
    targetTank.value = null;
  }
};
// ---------------------

const groupList = computed(() => {
  return Object.entries(importGroups.value).map(([date, group]) => {
    const sortedTanks = [...group.tanks].sort((a, b) => {
      const priceA = calculatePrice(a);
      const priceB = calculatePrice(b);
      return priceA - priceB;
    });

    return {
      ...group,
      date,
      tanks: sortedTanks
    };
  });
});

const isBeforeAvailableFrom = (tank: Tank): boolean => {
  const availableFrom = new Date(tank.available_from).getTime();
  return currentTime.value < availableFrom;
};

const visibleGroups = computed(() => {
  const start = currentPage.value * pageSize;
  return groupList.value.slice(start, start + pageSize);
});

const visibleTanks = computed(() => {
  return currentCriteria?.value?.required_tanks
    ? currentCriteria.value.required_tanks.slice(0, maxVisibleTanks)
    : [];
});

const hiddenTanks = computed(() => {
  return currentCriteria?.value?.required_tanks
    ? currentCriteria.value.required_tanks.slice(maxVisibleTanks)
    : [];
});

const isLastPage = computed(() => {
  return (currentPage.value + 1) * pageSize >= groupList.value.length;
});

const isCommander = computed(() => {
      return (userStore.groups.some(i => i.name === 'commander') ||
              userStore.groups.some(i => i.name === 'admin'))
});

const nextPage = () => {
  if (!isLastPage.value) currentPage.value++;
};

const prevPage = () => {
  if (currentPage.value > 0) currentPage.value--;
};

const isExpired = (tank: Tank): boolean => {
  const availableUntil = new Date(tank.available_until).getTime();
  return availableUntil < currentTime.value;
};

const isPurchased = (tank: Tank): boolean => {
  return tank.is_purchased;
};

const canAfford = (tank: Tank): boolean => {
  return calculatePrice(tank) <= team.value.balance;
}

const setInitialPage = () => {
  const now = new Date();

  let targetIndex = groupList.value.findIndex((group) => {
    if (!group.tanks || group.tanks.length === 0) return false;
    const activeFrom = new Date(group.tanks[0].available_from);
    const activeUntil = new Date(group.tanks[0].available_until);
    return now >= activeFrom && now <= activeUntil;
  });

  if (targetIndex === -1) {
    targetIndex = groupList.value.findIndex((group) => {
      if (!group.tanks || group.tanks.length === 0) return false;
      const activeUntil = new Date(group.tanks[0].available_until);
      return activeUntil > now;
    });
  }

  if (targetIndex !== -1) {
    currentPage.value = Math.floor(targetIndex / pageSize);
  } else if (groupList.value.length > 0) {
    currentPage.value = Math.floor((groupList.value.length - 1) / pageSize);
  }
};

const fetchImportGroups = async () => {
  try {
    const response = await fetch("/api/league/imports/grouped/");
    if (!response.ok) throw new Error("Failed to fetch import results.");

    const data: ImportGroups = await response.json();
    importGroups.value = data;

    setInitialPage();
  } catch (error) {
    console.error("Error fetching import results:", error);
  }
};

const fetchManufacturers = async () => {
  try {
    const response = await fetch(
      `/api/league/manufacturers/?team_name=${teamName.value}`
    );
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    const data = await response.json();
    allTanks.value = data.map((manufacturer: any) => manufacturer.tanks).flat();
  } catch (error) {
    console.error("There was a problem with the fetch operation:", error);
  }
};

const purchaseTank = async (tank: Tank) => {
  try {
    const response = await fetch(`/api/league/transactions/buy_imports/`, {
      method: "POST",
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
        'Authorization': getAuthToken(),
      },
      body: JSON.stringify({ import_id: tank.id }),
    });

    if (!response.ok) {
      throw new Error("Failed to purchase the tank.");
    }

    tank.is_purchased = true;
    team.value.balance -= calculatePrice(tank);
    alert(`Successfully purchased ${tank.tank_name}!`);
  } catch (error) {
    console.error("Error purchasing tank:", error);
    alert("An error occurred while purchasing the tank.");
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
}

const calculatePrice = (tank: Tank) => {
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

  return tank_price;
};

const viewCriteria = (criteria: Criteria | null) => {
  currentCriteria.value = criteria;
  showCriteriaDialog.value = true;
};

const formattedDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
};

const formattedTimeUTC = (isoString: string | undefined) => {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toISOString().slice(11, 16) + " UTC";
};

const formattedTimeLocal = (isoString: string | undefined) => {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }) + " Local";
};

onMounted(() => {
  fetchTeamDetails();
  fetchManufacturers();
  fetchImportGroups();

  timeInterval = setInterval(() => {
    currentTime.value = Date.now();
  }, 100);
});

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
  }
});
</script>

<style scoped>
.v-table td,
.v-table th {
  font-size: 0.95rem;
  padding: 8px 8px;
}

.v-card {
  max-width: 100%;
}

.purchased-tank td span {
  text-decoration: line-through;
  color: gray;
}

.expired-tank {
  background-color: darkred !important;
  color: white;
}

.text-line-through {
  text-decoration: line-through;
  color: gray;
}
</style>