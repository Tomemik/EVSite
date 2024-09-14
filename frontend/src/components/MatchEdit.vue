<template>
  <v-dialog v-model="localShowEditDialog" @update:model-value="close" max-width="1000px">
    <v-card>
      <v-card-title>Edit Match</v-card-title>
      <v-card-text>
        <v-form>
          <!-- Date and Time -->
          <v-text-field v-model="editForm.datetime" label="Date and Time" type="datetime-local"></v-text-field>

          <!-- Basic Match Information -->
          <v-text-field v-model="editForm.gamemode" label="Game Mode"></v-text-field>
          <v-text-field v-model="editForm.map_selection" label="Map Selection"></v-text-field>
          <v-text-field v-model="editForm.mode" label="Mode"></v-text-field>
          <v-text-field v-model="editForm.best_of_number" label="Best of Number" type="number"></v-text-field>
          <v-text-field v-model="editForm.money_rules" label="Money Rules"></v-text-field>
          <v-text-field v-model="editForm.special_rules" label="Special Rules"></v-text-field>

          <v-divider></v-divider>

          <!-- Teams Layout in Two Columns -->
          <v-row>
            <!-- Side 1 (Team 1) -->
            <v-col>
              <div v-for="(team, index) in editForm.sides.team_1" :key="index">
                <v-text-field v-model="team.team" label="Team Name"></v-text-field>
                <v-text-field v-model="team.tanks" label="Tanks (comma-separated)"></v-text-field>
                <v-btn @click="removeTeam('team_1', index)" color="red">Remove Team</v-btn>
              </div>
              <v-btn @click="addTeam('team_1')" color="primary">Add Team</v-btn>
            </v-col>

            <!-- VS text in center -->
            <v-col class="d-flex justify-center align-center">
              <p style="text-align:center; font-weight: bold;">vs</p>
            </v-col>

            <!-- Side 2 (Team 2) -->
            <v-col>
              <div v-for="(team, index) in editForm.sides.team_2" :key="index">
                <v-text-field v-model="team.team" label="Team Name"></v-text-field>
                <v-text-field v-model="team.tanks" label="Tanks (comma-separated)"></v-text-field>
                <v-btn @click="removeTeam('team_2', index)" color="red">Remove Team</v-btn>
              </div>
              <v-btn @click="addTeam('team_2')" color="primary">Add Team</v-btn>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-btn color="primary" @click="saveChanges">Save</v-btn>
        <v-btn color="secondary" @click="close">Cancel</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  detailedMatch: Object,
  showEditDialog: Boolean
});
const emit = defineEmits(['update:showEditDialog', 'updateMatch']);

const localShowEditDialog = ref(props.showEditDialog);

watch(() => props.showEditDialog, (newValue) => {
  localShowEditDialog.value = newValue;
});

watch(() => localShowEditDialog.value, (newValue) => {
  emit('update:showEditDialog', newValue);
});

const editForm = ref({
  datetime: '',
  gamemode: '',
  map_selection: '',
  mode: '',
  best_of_number: '',
  money_rules: '',
  special_rules: '',
  sides: {
    team_1: [{ team: '', tanks: '' }],
    team_2: [{ team: '', tanks: '' }],
  },
});

watch(() => props.detailedMatch, (newVal) => {
  if (newVal) {
    editForm.value = {
      datetime: new Date(newVal.datetime).toISOString().slice(0, 16),
      gamemode: newVal.gamemode,
      map_selection: newVal.map_selection,
      mode: newVal.mode,
      best_of_number: newVal.best_of_number,
      money_rules: newVal.money_rules,
      special_rules: newVal.special_rules,
      sides: {
        team_1: newVal.sides.team_1.map(team => ({
          team: team.team,
          tanks: team.tanks.map(tank => tank.name).join(', ') // Convert tanks array to a comma-separated string
        })),
        team_2: newVal.sides.team_2.map(team => ({
          team: team.team,
          tanks: team.tanks.map(tank => tank.name).join(', ') // Convert tanks array to a comma-separated string
        })),
      },
    };
  }
}, { immediate: true });

const addTeam = (side) => {
  editForm.value.sides[side].push({ team: '', tanks: '' });
};

const removeTeam = (side, index) => {
  if (editForm.value.sides[side].length > 1) {
    editForm.value.sides[side].splice(index, 1);
  } else {
    // Optionally, you could show a warning or disable removal if only one team remains
  }
};

const saveChanges = () => {
  // Convert tanks comma-separated string back to array
  const formatTanks = (teams) => teams.map(team => ({
    team: team.team,
    tanks: team.tanks.split(',').map(tank => ({ name: tank.trim() }))
  }));

  const updatedMatch = {
    datetime: editForm.value.datetime,
    gamemode: editForm.value.gamemode,
    map_selection: editForm.value.map_selection,
    mode: editForm.value.mode,
    best_of_number: editForm.value.best_of_number,
    money_rules: editForm.value.money_rules,
    special_rules: editForm.value.special_rules,
    sides: {
      team_1: formatTanks(editForm.value.sides.team_1),
      team_2: formatTanks(editForm.value.sides.team_2),
    }
  };

  emit('updateMatch', updatedMatch);
  close();
};

const close = () => {
  localShowEditDialog.value = false;
};
</script>