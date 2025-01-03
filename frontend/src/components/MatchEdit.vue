<template>
  <v-dialog v-model="localShowEditDialog" @update:model-value="close" max-width="1000px">
    <v-card>
      <v-card-title>Edit Match</v-card-title>
      <v-card-text>
        <v-form>
          <v-text-field v-model="editForm.datetime" label="Date and Time" type="datetime-local"></v-text-field>

          <v-select
            v-model="editForm.mode"
            :items="modeOptions"
            label="Mode"
          ></v-select>
          <v-select
            v-model="editForm.gamemode"
            :items="gamemodeOptions"
            label="Game Mode"
          ></v-select>

          <v-text-field v-model="editForm.map_selection" label="Map Selection"></v-text-field>
          <v-select
            v-model="editForm.best_of_number"
            label="Best of Number"
            :items="bestOfOptions"
          ></v-select>
          <v-text-field v-model="editForm.special_rules" label="Special Rules"></v-text-field>
          <v-select
            v-model="editForm.money_rules"
            :items="moneyRulesOptions"
            label="Money Rules"
          ></v-select>

          <v-divider></v-divider>

          <v-row>
            <v-col>
              <div v-for="(team, index) in editForm.teammatch_set.team_1" :key="index">
                <v-select
                  v-model="team.team"
                  :items="teamOptions"
                  label="Team Name"
                  item-text="name"
                  item-value="name"
                  @change="onTeamSelect('team_1', index)"
                ></v-select>

                <v-select
                  v-model="team.tanks"
                  :items="getTeamTanks('team_1', index)"
                  label="Tanks"
                  multiple
                  chips
                  item-value="id"
                  item-text="tank.name"
                ></v-select>

                <v-btn @click="removeTeam('team_1', index)" color="red">Remove Team</v-btn>
              </div>
              <v-btn @click="addTeam('team_1')" color="primary">Add Team</v-btn>
            </v-col>

            <v-col class="d-flex justify-center align-center">
              <p style="text-align:center; font-weight: bold;">vs</p>
            </v-col>

            <v-col>
              <div v-for="(team, index) in editForm.teammatch_set.team_2" :key="index">
                <v-select
                  v-model="team.team"
                  :items="teamOptions"
                  label="Team Name"
                  item-text="name"
                  item-value="name"
                  @change="onTeamSelect('team_2', index)"
                ></v-select>

                <v-select
                  v-model="team.tanks"
                  :items="getTeamTanks('team_2', index)"
                  label="Tanks"
                  multiple
                  chips
                  item-value="id"
                  item-text="tank.name"
                ></v-select>

                <v-btn @click="removeTeam('team_2', index)" color="red">Remove Team</v-btn>
              </div>
              <v-btn @click="addTeam('team_2')" color="primary">Add Team</v-btn>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-btn color="primary" @click="saveChanges">Save</v-btn>
        <v-btn color="error" @click="close">Cancel</v-btn>
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
    team_1: [{ team: '', tanks: [] }],
    team_2: [{ team: '', tanks: [] }],
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
  teamOptions.value = props.allTeamDetails.map(team => ({
    title: team.name,
    id: team.id,
  }));
};

const updateAvailableTeams = () => {
  const allTeams = [
    ...editForm.value.teammatch_set.team_1.map(team => team.team),
    ...editForm.value.teammatch_set.team_2.map(team => team.team)
  ];

  teamOptions.value = props.allTeamDetails
    .filter(team => !allTeams.includes(team.name))
    .map(team => ({
      title: team.name,
      id: team.id,
    }))
    .sort((a, b) => a.title.localeCompare(b.title));
};

watch(() => editForm.value.teammatch_set, () => {
  updateAvailableTeams();
}, { deep: true });

watch(() => props.allTeamDetails, (newData) => {
  if (newData) {
    updateAvailableTeams();
    updateTeamOptions();
  }
}, { immediate: true });

watch(() => props.showEditDialog, (newValue) => {
  localShowEditDialog.value = newValue;
});

watch(() => localShowEditDialog.value, (newValue) => {
  emit('update:showEditDialog', newValue);
});

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
          tanks: team.tanks.map(tank => tank.id)
        })),
        team_2: newVal.sides.team_2.map(team => ({
          team: team.team,
          tanks: team.tanks.map(tank => tank.id)
        })),
      },
    };
  }
}, { immediate: true });

const onTeamSelect = (side, index) => {
  editForm.value.teammatch_set[side][index].tanks = [];
};

const getTeamTanks = (side, index) => {
  const selectedTeamName = editForm.value.teammatch_set[side][index].team;
  const mode = editForm.value.mode; // Get the current mode

  const team = props.allTeamDetails.find(t => t.name === selectedTeamName);

  if (team) {
    return team.tanks
      .filter(tank => {
        // Return tanks based on the current mode
        if (mode === 'traditional') {
          // Only include available traditional tanks if the mode is "traditional"
          return tank.is_trad && tank.available;
        } else {
          // Return all tanks that are not traditional (is_trad is false)
          return !tank.is_trad;
        }
      })
      .map(tank => ({
        id: tank.id,
        title: tank.tank.name,
      }));
  }

  return [];
};

const getTankNameById = (teamName, tankId) => {
  const tanks = getTeamTanksByName(teamName);
  const tank = tanks.find(t => t.id === tankId);
  return tank ? tank.name : '';
};

const getTeamTanksByName = (name) => {
  const team = props.allTeamDetails.find(t => t.name === name);

  if (team) {
    console.log(team.tanks)
    return team.tanks.map(tank => ({
      id: tank.id,
      name: tank.tank.name,
      battle_rating: tank.tank.battle_rating // Ensure battle_rating exists in the tank object
    }));
  }

  return [];
};

const getTeamId = (teamName) => {
  return props.allTeamDetails.find(t => t.name === teamName).id;
}

const addTeam = (side) => {
  editForm.value.teammatch_set[side].push({ team: '', tanks: [] });
};

const removeTeam = (side, index) => {
  if (editForm.value.teammatch_set[side].length > 1) {
    editForm.value.teammatch_set[side].splice(index, 1);
  }
};

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
      return editForm.value.teammatch_set[side].map(team => ({
        team: team.team,
        tanks: team.tanks
          .map(tankId => {
            const tankData = getTeamTanksByName(team.team).find(t => t.id === tankId);
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
          .sort((a, b) => b.tank.battle_rating - a.tank.battle_rating),
        side: side,
      }));
    }).flat()
  };

  console.log(updatedMatch);
  emit('updateMatch', updatedMatch);
  close();
};

const close = () => {
  localShowEditDialog.value = false;
};
</script>

<style scoped>
.v-select {
  margin-bottom: 10px;
}
</style>