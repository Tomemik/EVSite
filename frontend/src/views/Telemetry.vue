<template>
  <v-container
    fluid
    class="h-100 d-flex flex-column pa-0 bg-grey-lighten-4 position-relative"
    @dragenter.prevent="isDragging = true"
    @dragover.prevent
  >
    <v-overlay
      :model-value="isDragging"
      class="align-center justify-center"
      contained
      z-index="999"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @dragover.prevent
    >
      <v-card class="bg-primary text-center pa-10 rounded-xl d-flex flex-column align-center justify-center" style="border: 4px dashed white; pointer-events: none;">
        <v-icon size="96" class="mb-4">mdi-file-upload-outline</v-icon>
        <div class="text-h3 font-weight-bold">Drop .wrpl files here</div>
        <div class="text-h6 mt-2">Files will be parsed instantly for telemetry viewing</div>
      </v-card>
    </v-overlay>

    <v-toolbar color="surface" class="border-b flex-shrink-0" density="compact">
      <v-toolbar-title class="text-subtitle-1 font-weight-bold">
        <v-icon start icon="mdi-magnify-scan"></v-icon>
        Replay Analyzer
      </v-toolbar-title>
      <v-spacer></v-spacer>

      <div class="d-flex align-center" style="width: 600px;">
        <v-file-input
          v-model="replayFiles"
          accept=".wrpl"
          multiple
          label="Select or Drop .wrpl files"
          density="compact"
          variant="outlined"
          hide-details
          prepend-icon=""
          prepend-inner-icon="mdi-paperclip"
          class="mr-2"
        ></v-file-input>

        <v-btn
          color="primary"
          @click="parseTemporaryReplays"
          :loading="isParsing"
          :disabled="!replayFiles || replayFiles.length === 0"
        >
          Parse Replays
        </v-btn>

        <v-btn
          v-if="transientData"
          color="error"
          variant="tonal"
          class="ml-2"
          @click="clearSessionData"
          prepend-icon="mdi-delete"
        >
          Clear
        </v-btn>
      </div>
    </v-toolbar>

    <div class="flex-grow-1 overflow-hidden">
      <TelemetryDashboard
        :telemetry-data="transientData"
        :is-loading-telemetry="isParsing"
      />
    </div>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import TelemetryDashboard from '@/components/TelemetryDashboard.vue';
import { getAuthToken } from "@/config/api/user.ts";

const STORAGE_KEY = 'temp_telemetry_data';

const replayFiles = ref([]);
const transientData = ref(null);
const isParsing = ref(false);
const isDragging = ref(false);

// --- 1. LOAD FROM SESSION ON MOUNT ---
onMounted(() => {
  try {
    const savedData = sessionStorage.getItem(STORAGE_KEY);
    if (savedData) {
      transientData.value = JSON.parse(savedData);
    }
  } catch (e) {
    console.error("Failed to load temporary telemetry from session storage", e);
    sessionStorage.removeItem(STORAGE_KEY);
  }
});

// --- DRAG AND DROP HANDLER ---
const handleDrop = (event) => {
  isDragging.value = false;
  const droppedFiles = Array.from(event.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.wrpl'));

  if (droppedFiles.length > 0) {
    const newFiles = [...replayFiles.value];
    droppedFiles.forEach(file => {
      // Append only if not already staged
      if (!newFiles.some(existing => existing.name === file.name)) {
        newFiles.push(file);
      }
    });
    replayFiles.value = newFiles;
  }
};

// --- PARSER ---
const parseTemporaryReplays = async () => {
  if (!replayFiles.value || replayFiles.value.length === 0) return;

  isParsing.value = true;
  const formData = new FormData();

  replayFiles.value.forEach(file => {
    formData.append('replay_files', file);
  });

  try {
    const res = await fetch(`/api/league/replays/parse-temp/`, {
      method: 'POST',
      headers: { 'Authorization': getAuthToken() },
      body: formData
    });

    if (res.ok) {
      const data = await res.json();
      transientData.value = data.parsed_telemetry;

      // Save to session storage
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data.parsed_telemetry));
      } catch (e) {
        console.warn("Telemetry data exceeded 5MB limit. It will not survive a page refresh.", e);
        sessionStorage.removeItem(STORAGE_KEY);
      }

    } else {
      console.error("Failed to parse replays");
    }
  } catch (err) {
    console.error("Upload error:", err);
  } finally {
    isParsing.value = false;
  }
};

// --- CLEAR FUNCTION ---
const clearSessionData = () => {
  transientData.value = null;
  replayFiles.value = [];
  sessionStorage.removeItem(STORAGE_KEY);
};
</script>