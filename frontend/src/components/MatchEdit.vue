<template>
  <v-dialog v-model="localShowEditDialog" @update:model-value="close" max-width="1000px">
    <v-card class="rounded-lg">
      <v-toolbar color="primary" density="compact">
        <v-toolbar-title class="text-subtitle-1 font-weight-bold">
          <v-icon start icon="mdi-pencil"></v-icon>
          Edit Match Details
        </v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-6">
        <v-form>
          <v-row dense>
            <v-col cols="12">
              <v-text-field
                v-model="editForm.datetime"
                label="Date and Time"
                type="datetime-local"
                prepend-inner-icon="mdi-calendar-clock"
                variant="outlined"
                density="comfortable"
              ></v-text-field>
            </v-col>
          </v-row>

          <v-row dense>
            <v-col cols="12" md="6">
              <v-select
                v-model="editForm.mode"
                :items="modeOptions"
                label="Mode"
                prepend-inner-icon="mdi-controller"
                variant="outlined"
                density="compact"
              ></v-select>
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="editForm.gamemode"
                :items="gamemodeOptions"
                label="Game Mode"
                prepend-inner-icon="mdi-controller-classic"
                variant="outlined"
                density="compact"
              ></v-select>
            </v-col>
          </v-row>

          <v-row dense>
            <v-col cols="12" md="4">
              <v-select
                v-model="editForm.money_rules"
                :items="moneyRulesOptions"
                label="Money Rules"
                prepend-inner-icon="mdi-cash"
                variant="outlined"
                density="compact"
              ></v-select>
            </v-col>
            <v-col cols="12" md="4">
              <v-select
                v-model="editForm.best_of_number"
                label="Format (Best of)"
                :items="bestOfOptions"
                prepend-inner-icon="mdi-trophy-outline"
                variant="outlined"
                density="compact"
              ></v-select>
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="editForm.map_selection"
                label="Map Selection"
                prepend-inner-icon="mdi-map-marker"
                variant="outlined"
                density="compact"
              ></v-text-field>
            </v-col>
          </v-row>

          <v-row dense>
            <v-col cols="12">
              <v-text-field
                v-model="editForm.special_rules"
                label="Special Rules"
                prepend-inner-icon="mdi-alert-circle-outline"
                variant="outlined"
                density="compact"
              ></v-text-field>
            </v-col>
          </v-row>

          <v-divider class="my-6"></v-divider>

          <v-row>
            <v-col cols="12" md="5">
              <div class="text-subtitle-1 mb-2 text-center font-weight-bold text-primary">Team 1</div>

              <div v-for="(team, teamIndex) in editForm.teammatch_set.team_1" :key="teamIndex" class="mb-4">
                <v-card variant="outlined" class="border-grey">
                  <v-card-item class="bg-grey-lighten-1 py-2">
                    <div class="d-flex align-center">
                      <v-autocomplete
                        v-model="team.team"
                        :items="teamOptions"
                        label="Select Team"
                        item-title="title"
                        item-value="title"
                        hide-details
                        variant="plain"
                        density="compact"
                        class="font-weight-bold"
                        @update:model-value="onTeamSelect('team_1', teamIndex)"
                      >
                        <template v-slot:selection="{ item }">
                          <span class="text-primary">{{ item.title }}</span>
                        </template>
                      </v-autocomplete>
                      <v-btn
                        icon="mdi-close"
                        variant="text"
                        color="error"
                        size="small"
                        @click="removeTeam('team_1', teamIndex)"
                      ></v-btn>
                    </div>
                  </v-card-item>

                  <v-divider></v-divider>

                  <v-card-text class="pa-2">
                    <div
                      v-for="(tankEntry, tankIndex) in team.tanks"
                      :key="tankIndex"
                      class="d-flex align-center mb-1"
                    >
                      <v-icon icon="mdi-tank" size="small" color="grey-lighten-1" class="mr-2"></v-icon>
                      <v-autocomplete
                        class="my-1"
                        v-model="tankEntry.id"
                        :items="getTeamTanks('team_1', teamIndex, tankIndex)"
                        label="Select Tank"
                        item-title="title"
                        item-value="id"
                        placeholder="Add a tank..."
                        hide-details
                        variant="underlined"
                        density="compact"
                        @update:model-value="onTankChange('team_1', teamIndex, tankIndex)"
                      ></v-autocomplete>

                      <v-btn
                        v-if="tankIndex !== team.tanks.length - 1"
                        icon="mdi-close"
                        size="x-small"
                        variant="text"
                        color="grey"
                        class="ml-1"
                        @click="removeTank('team_1', teamIndex, tankIndex)"
                      ></v-btn>
                      <div v-else style="width: 28px; margin-left: 4px;"></div>
                    </div>
                  </v-card-text>
                </v-card>
              </div>
              <v-btn block variant="tonal" color="primary" prepend-icon="mdi-plus" @click="addTeam('team_1')">Add Team</v-btn>
            </v-col>

            <v-col cols="12" md="2" class="d-flex justify-center align-center">
               <div class="text-h5 text-disabled font-italic font-weight-black">VS</div>
            </v-col>

            <v-col cols="12" md="5">
              <div class="text-subtitle-1 mb-2 text-center font-weight-bold text-error">Team 2</div>

              <div v-for="(team, teamIndex) in editForm.teammatch_set.team_2" :key="teamIndex" class="mb-4">
                <v-card variant="outlined" class="border-grey">
                  <v-card-item class="bg-grey-lighten-1 py-2">
                    <div class="d-flex align-center">
                      <v-autocomplete
                        v-model="team.team"
                        :items="teamOptions"
                        label="Select Team"
                        item-title="title"
                        item-value="title"
                        hide-details
                        variant="plain"
                        density="compact"
                        class="font-weight-bold"
                        @update:model-value="onTeamSelect('team_2', teamIndex)"
                      >
                        <template v-slot:selection="{ item }">
                          <span class="text-error">{{ item.title }}</span>
                        </template>
                      </v-autocomplete>
                      <v-btn
                        icon="mdi-close"
                        variant="text"
                        color="error"
                        size="small"
                        @click="removeTeam('team_2', teamIndex)"
                      ></v-btn>
                    </div>
                  </v-card-item>

                  <v-divider></v-divider>

                   <v-card-text class="pa-2">
                    <div
                      v-for="(tankEntry, tankIndex) in team.tanks"
                      :key="tankIndex"
                      class="d-flex align-center mb-1"
                    >
                      <v-icon icon="mdi-tank" size="small" color="grey-lighten-1" class="mr-2"></v-icon>
                      <v-autocomplete
                        class="my-1"
                        v-model="tankEntry.id"
                        :items="getTeamTanks('team_2', teamIndex, tankIndex)"
                        label="Select Tank"
                        item-title="title"
                        item-value="id"
                        placeholder="Add a tank..."
                        hide-details
                        variant="underlined"
                        density="compact"
                        @update:model-value="onTankChange('team_2', teamIndex, tankIndex)"
                      ></v-autocomplete>

                      <v-btn
                        v-if="tankIndex !== team.tanks.length - 1"
                        icon="mdi-close"
                        size="x-small"
                        variant="text"
                        color="grey"
                        class="ml-1"
                        @click="removeTank('team_2', teamIndex, tankIndex)"
                      ></v-btn>
                      <div v-else style="width: 28px; margin-left: 4px;"></div>
                    </div>
                  </v-card-text>
                </v-card>
              </div>
              <v-btn block variant="tonal" color="primary" prepend-icon="mdi-plus" @click="addTeam('team_2')">Add Team</v-btn>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn color="error" variant="text" prepend-icon="mdi-close" @click="close">Cancel</v-btn>
        <v-btn color="primary" variant="elevated" prepend-icon="mdi-content-save" @click="saveChanges">Save Changes</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  detailedMatch: Object,
  showEditDialog: Boolean,
  allTeamDetails: Array,
});
const emit = defineEmits(['update:showEditDialog', 'updateMatch']);

const localShowEditDialog = ref(props.showEditDialog);
const teamOptions = ref([]);

// Structure: tanks is now an array of objects { id: number | null }
const editForm = ref({
  id: '',
  datetime: '',
  gamemode: '',
  map_selection: '',
  mode: '',
  best_of_number: '',
  money_rules: '',
  special_rules: '',
  teammatch_set: {
    team_1: [{ team: '', tanks: [{ id: null }] }],
    team_2: [{ team: '', tanks: [{ id: null }] }],
  },
});

const gamemodeOptions = [
  { value: 'annihilation', title: 'Annihilation' },
  { value: 'domination', title: 'Domination' },
  { value: 'flag_tank', title: 'Flag Tank' }
];

const bestOfOptions = [
  { value: '3', title: '3' },
  { value: '5', title: '5' },
];

const modeOptions = [
  { value: 'traditional', title: 'Traditional' },
  { value: 'advanced', title: 'Advanced' },
  { value: 'evolved', title: 'Evolved' }
];

const moneyRulesOptions = [
  { value: 'money_rule', title: 'Money Rule' },
  { value: 'even_split', title: 'Even Split' },
  { value: 'none', title: 'None' }
];

const updateTeamOptions = () => {
  if (!props.allTeamDetails) return;
  teamOptions.value = props.allTeamDetails.map(team => ({
    title: team.name,
    id: team.id,
  }));
};

const updateAvailableTeams = () => {
  if (!props.allTeamDetails) return;

  const allTeams = [
    ...editForm.value.teammatch_set.team_1.map(team => team.team),
    ...editForm.value.teammatch_set.team_2.map(team => team.team)
  ];

  teamOptions.value = props.allTeamDetails
    .filter(team => !allTeams.includes(team.name)) // Only filter if you want to prevent duplicate teams
    .map(team => ({
      title: team.name,
      id: team.id,
    }))
    .sort((a, b) => a.title.localeCompare(b.title));
};

// --- Watchers ---

watch(() => props.showEditDialog, (newValue) => {
  localShowEditDialog.value = newValue;
});

watch(() => localShowEditDialog.value, (newValue) => {
  emit('update:showEditDialog', newValue);
});

watch(() => props.allTeamDetails, (newData) => {
  if (newData) {
    updateTeamOptions();
  }
}, { immediate: true });

// Initialize form when detailedMatch changes
watch(() => props.detailedMatch, (newVal) => {
  if (newVal) {
    editForm.value = {
      id: newVal.id,
      datetime: new Date(newVal.datetime).toISOString().slice(0, 16),
      gamemode: newVal.gamemode,
      map_selection: newVal.map_selection,
      mode: newVal.mode,
      best_of_number: newVal.best_of_number,
      money_rules: newVal.money_rules,
      special_rules: newVal.special_rules,
      teammatch_set: {
        team_1: newVal.sides.team_1.map(team => ({
          team: team.team,
          // Convert IDs to objects and append one empty slot
          tanks: [...team.tanks.map(tank => ({ id: tank.id })), { id: null }]
        })),
        team_2: newVal.sides.team_2.map(team => ({
          team: team.team,
          // Convert IDs to objects and append one empty slot
          tanks: [...team.tanks.map(tank => ({ id: tank.id })), { id: null }]
        })),
      },
    };
  }
}, { immediate: true });


// --- Form Logic ---

const onTeamSelect = (side, index) => {
  // When team changes, reset tanks to one empty slot
  editForm.value.teammatch_set[side][index].tanks = [{ id: null }];
  updateAvailableTeams();
};

const onTankChange = (side, teamIndex, tankIndex) => {
  const currentTeam = editForm.value.teammatch_set[side][teamIndex];
  // If we just edited the last row, add a new empty row
  if (tankIndex === currentTeam.tanks.length - 1 && currentTeam.tanks[tankIndex].id) {
    currentTeam.tanks.push({ id: null });
  }
};

const removeTank = (side, teamIndex, tankIndex) => {
  const currentTeam = editForm.value.teammatch_set[side][teamIndex];
  // Allow removing unless it's the only one (optional, keeping 1 empty is usually good UX)
  if (currentTeam.tanks.length > 1) {
    currentTeam.tanks.splice(tankIndex, 1);
  } else {
    // If it's the last one, just clear the value
    currentTeam.tanks[0].id = null;
  }
};

const addTeam = (side) => {
  editForm.value.teammatch_set[side].push({ team: '', tanks: [{ id: null }] });
};

const removeTeam = (side, index) => {
  if (editForm.value.teammatch_set[side].length > 1) {
    editForm.value.teammatch_set[side].splice(index, 1);
    updateAvailableTeams();
  } else {
    // Optional: alert user they can't have 0 teams on a side
    alert("At least one team is required per side.");
  }
};

// --- Helpers ---

const getTeamTanks = (side, teamIndex, currentTankRowIndex) => {
  const selectedTeamName = editForm.value.teammatch_set[side][teamIndex].team;
  if (!selectedTeamName) return [];

  const mode = editForm.value.mode;
  const team = props.allTeamDetails.find(t => t.name === selectedTeamName);

  if (team) {
    const currentTeamRows = editForm.value.teammatch_set[side][teamIndex].tanks;
    const usedIds = currentTeamRows
      .map((row, idx) => {
        return idx !== currentTankRowIndex ? row.id : null;
      })
      .filter(id => id !== null);

    return team.tanks
      .filter(tank => {
        const isModeValid = (mode === 'traditional')
          ? (tank.is_trad && tank.available)
          : (!tank.is_trad);

        const isNotUsed = !usedIds.includes(tank.id);

        return isModeValid && isNotUsed;
      })
      .map(tank => ({
        id: tank.id,
        title: tank.tank.name,
      }));
  }
  return [];
};

const getTeamTanksByName = (name) => {
  const team = props.allTeamDetails.find(t => t.name === name);
  if (team) {
    return team.tanks.map(tank => ({
      id: tank.id,
      name: tank.tank.name,
      battle_rating: tank.tank.battle_rating
    }));
  }
  return [];
};

const getTeamId = (teamName) => {
  const t = props.allTeamDetails.find(t => t.name === teamName);
  return t ? t.id : null;
}

// --- Save ---

const saveChanges = () => {
  const updatedMatch = {
    id: props.detailedMatch.id,
    datetime: editForm.value.datetime,
    gamemode: editForm.value.gamemode,
    map_selection: editForm.value.map_selection,
    mode: editForm.value.mode,
    best_of_number: editForm.value.best_of_number,
    money_rules: editForm.value.money_rules,
    special_rules: editForm.value.special_rules,

    teammatch_set: Object.keys(editForm.value.teammatch_set).map(side => {
      return editForm.value.teammatch_set[side].map(team => {

        const tankReferenceList = getTeamTanksByName(team.team);

        const cleanedTanks = team.tanks
          .filter(t => t.id)
          .map(t => t.id)
          .map(tankId => {
            const tankData = tankReferenceList.find(ref => ref.id === tankId);
            if (!tankData) return null;

            return {
              id: tankId,
              tank: {
                name: tankData.name,
                id: tankId,
                battle_rating: tankData.battle_rating
              },
              team: getTeamId(team.team)
            };
          })
          .filter(t => t !== null)
          .sort((a, b) => b.tank.battle_rating - a.tank.battle_rating);

        return {
          team: team.team,
          tanks: cleanedTanks,
          side: side,
        };
      });
    }).flat()
  };

  console.log("Saving Updated Match:", updatedMatch);
  emit('updateMatch', updatedMatch);
  close();
};

const close = () => {
  localShowEditDialog.value = false;
};
</script>

<style scoped>
.border-grey {
  border-color: #BDBDBD !important;
}
</style>