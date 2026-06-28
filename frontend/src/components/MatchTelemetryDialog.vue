<template>
  <v-dialog v-model="localShowDialog" @update:model-value="close" fullscreen transition="dialog-bottom-transition">
    <v-card class="bg-grey-lighten-4 d-flex flex-column">
      <v-toolbar color="deep-purple-darken-3" density="compact">
        <v-toolbar-title class="text-subtitle-1 font-weight-bold">
          <v-icon start icon="mdi-map-marker-path"></v-icon>
          Match Replay Analytics
        </v-toolbar-title>
        <v-spacer></v-spacer>

        <div class="mr-4" style="width: 250px;">
          <v-select
            v-model="selectedRound"
            :items="availableRounds"
            item-title="title"
            item-value="round_number"
            label="Select Round"
            density="compact"
            variant="solo-filled"
            hide-details
            prepend-inner-icon="mdi-counter"
            @update:model-value="loadRoundTelemetry"
            :loading="isLoadingRounds"
          ></v-select>
        </div>

        <v-btn icon @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <TelemetryDashboard
        :telemetry-data="telemetryData"
        :is-loading-telemetry="isLoadingTelemetry"
      />

    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue';
import { getAuthToken } from "@/config/api/user.ts";
import TelemetryDashboard from './TelemetryDashboard.vue';

const props = defineProps({
  detailedMatch: Object,
  showDialog: Boolean
});

const emit = defineEmits(['update:showDialog']);
const localShowDialog = ref(props.showDialog);

const availableRounds = ref([]);
const selectedRound = ref(null);
const telemetryData = ref(null);
const isLoadingRounds = ref(false);
const isLoadingTelemetry = ref(false);

const close = () => {
  emit('update:showDialog', false);
};

watch(() => props.showDialog, async (newVal) => {
  localShowDialog.value = newVal;
  if (newVal && props.detailedMatch) {
    telemetryData.value = null;
    selectedRound.value = null;
    await fetchAvailableRounds();
  }
});

const fetchAvailableRounds = async () => {
  if (!props.detailedMatch || !props.detailedMatch.id) return;
  isLoadingRounds.value = true;
  try {
    const res = await fetch(`/api/league/matches/${props.detailedMatch.id}/rounds/`, {
      headers: { 'Authorization': getAuthToken() }
    });
    if (res.ok) {
      const data = await res.json();
      const rounds = data.results !== undefined ? data.results : data;
      availableRounds.value = rounds
        .filter(r => r.is_verified)
        .map(r => ({
          title: `Round ${r.round_number} - ${r.map_name || 'Unknown'}`,
          round_number: r.round_number
        }));
    }
  } catch (e) {
    console.error('Error fetching rounds:', e);
  } finally {
    isLoadingRounds.value = false;
  }
};

const loadRoundTelemetry = async () => {
  if (!selectedRound.value) return;
  isLoadingTelemetry.value = true;
  telemetryData.value = null;
  try {
    const res = await fetch(`/api/league/matches/${props.detailedMatch.id}/replays/${selectedRound.value}/telemetry/`, {
      headers: { 'Authorization': getAuthToken() }
    });
    if (res.ok) {
      telemetryData.value = await res.json();
    }
  } catch (err) {
    console.error("Error retrieving telemetry:", err);
  } finally {
    isLoadingTelemetry.value = false;
  }
};
</script>