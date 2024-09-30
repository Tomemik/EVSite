<template>
  <v-dialog v-model="localShowDetailsDialog" @update:model-value="close" max-width="800px">
    <v-card>
      <v-card-title>Match Details</v-card-title>
      <v-card-text v-if="detailedMatch">
        <!-- Date and Time -->
        <p><strong>Date:</strong> {{ formatDateTime(detailedMatch.datetime) }}</p>

        <!-- Basic Match Information -->
        <v-divider></v-divider>
        <p><strong>Mode:</strong> {{ detailedMatch.mode }}</p>
        <p><strong>Game Mode:</strong> {{ detailedMatch.gamemode }}</p>
        <p><strong>Map Selection:</strong> {{ detailedMatch.map_selection }}</p>
        <p><strong>Best of Number:</strong> {{ detailedMatch.best_of_number }}</p>
        <p><strong>Special Rules:</strong> {{ detailedMatch.special_rules || 'None' }}</p>
        <p><strong>Money Rules:</strong> {{ detailedMatch.money_rules }}</p>

        <v-divider></v-divider>

        <v-row>
          <v-col>
            <div v-for="team in detailedMatch.sides.team_1" :key="team.team">
              <p><strong>{{ team.team }}:</strong></p>

              <ul style="list-style-type: none; padding-left: 0;">
                <li v-for="tank in team.tanks" :key="tank.id">{{ tank.tank.name }}</li>
              </ul>
            </div>
          </v-col>

          <v-col class="d-flex justify-center align-center">
            <p style="text-align:center; font-weight: bold;">vs</p>
          </v-col>

          <v-col class="d-flex flex-column align-end">
            <div v-for="team in detailedMatch.sides.team_2" :key="team.team">
              <p><strong>{{ team.team }}:</strong></p>

              <ul style="list-style-type: none; padding-left: 0;">
                <li v-for="tank in team.tanks" :key="tank.id">{{ tank.tank.name }}</li>
              </ul>
            </div>
          </v-col>
        </v-row>

      </v-card-text>

      <v-card-actions>
        <v-btn color="success" @click="openResultView">Result</v-btn>
        <v-spacer></v-spacer>
        <v-btn v-if="userStore.groups.some(i => ['commander', 'judge', 'admin'].includes(i.name))" color="primary" @click="toggleEditMode">Edit</v-btn>
        <v-btn color="error" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>

  </v-dialog>
</template>

<script setup>
import {ref, watch} from 'vue';
import {useUserStore} from "../config/store.ts";

const userStore = useUserStore()

const props = defineProps(['detailedMatch', 'showDetailsDialog']);
const emit = defineEmits(['update:showDetailsDialog', 'editMode', 'resultView']);

const localShowDetailsDialog = ref(props.showDetailsDialog);

watch(() => props.showDetailsDialog, (newValue) => {
  localShowDetailsDialog.value = newValue;
});

const updateShowDetailsDialog = (value) => {
  emit('update:showDetailsDialog', value);
};

const formatDateTime = (datetime) => {
  const options = {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false
  };
  return new Date(datetime).toLocaleString(undefined, options);
};

const openResultView = () => {
  emit('resultView');
}

const toggleEditMode = () => {
  emit('editMode');
};

const close = () => {
  updateShowDetailsDialog(false);
}
</script>