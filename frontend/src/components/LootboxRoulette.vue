<template>
  <v-dialog v-model="isOpen" max-width="800px" persistent>
    <v-card class="grey darken-4 white--text">
      <v-card-title class="text-center justify-center pt-6 text-h4 font-weight-bold amber--text text--lighten-2">
        Opening {{ boxName }}...
      </v-card-title>

      <v-card-text class="pb-6">
        <div class="roulette-wrapper mt-4 mb-4" ref="rouletteContainer">
          <!-- The golden center selector line -->
          <div class="roulette-selector"></div>

          <!-- The moving track -->
          <div
            class="roulette-track"
            :style="{
              transform: `translateX(${rouletteOffset}px)`,
              transition: isSpinning ? 'transform 7s cubic-bezier(0.1, 0.8, 0.1, 1)' : 'none'
            }"
            @transitionend="onSpinEnd"
          >
            <!-- The items -->
            <div
              v-for="(item, index) in rouletteItems"
              :key="index"
              class="roulette-item"
              :class="{ 'winner-highlight': showWinner && index === winnerIndex }"
            >
              <div class="item-tier">
                {{ 'REWARD' }}
              </div>
              <div class="item-name font-weight-bold">{{ item.name }}</div>
              <v-icon size="40" :color="showWinner && index === winnerIndex ? 'white' : 'grey darken-2'" class="mt-2">
                mdi-tank
              </v-icon>
            </div>
          </div>
        </div>
      </v-card-text>

      <!-- Claim Button (appears after spin) -->
      <v-card-actions class="justify-center pb-6" v-if="showWinner">
        <v-btn color="success" elevation="3" x-large @click="claimReward">
          Claim {{ wonTankName }}!
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  boxName: { type: String, default: 'Loot Box' },
  wonTankName: { type: String, required: true },
  possibleItems: { type: Array, default: () => [] }
});

const emit = defineEmits(['update:modelValue', 'claimed']);

// Component state
const isOpen = ref(props.modelValue);
const isSpinning = ref(false);
const showWinner = ref(false);
const rouletteItems = ref([]);
const rouletteOffset = ref(0);
const winnerIndex = 50;
const rouletteContainer = ref(null);

// Watch for the dialog opening from the parent
watch(() => props.modelValue, (newVal) => {
  isOpen.value = newVal;
  if (newVal) {
    startSpin();
  }
});

// Update parent if dialog closes
watch(isOpen, (newVal) => {
  emit('update:modelValue', newVal);
});

const startSpin = async () => {
  showWinner.value = false;
  isSpinning.value = false;
  rouletteOffset.value = 0;

  // Use the actual box contents, or fallback to mock tanks if none are provided
  const availableTanks = props.possibleItems && props.possibleItems.length > 0
    ? props.possibleItems
    : ['T-34', 'Tiger H1', 'M4 Sherman', 'IS-2', 'Panther D', 'Cromwell V', 'Chi-Nu'];

  rouletteItems.value = Array.from({ length: 70 }, (_, i) => {
    // Put the actual winner at the target index
    if (i === winnerIndex) return { name: props.wonTankName };
    // Fill the rest randomly from the ACTUAL box contents!
    return { name: availableTanks[Math.floor(Math.random() * availableTanks.length)] };
  });

  await nextTick();

  setTimeout(() => {
    if (!rouletteContainer.value) return;

    const itemWidth = 150;
    const containerWidth = rouletteContainer.value.clientWidth;
    const randomJitter = Math.floor(Math.random() * 120) - 60;

    const targetOffset = (containerWidth / 2) - (winnerIndex * itemWidth) - (itemWidth / 2) + randomJitter;

    isSpinning.value = true;
    rouletteOffset.value = targetOffset;
  }, 150);
};

const onSpinEnd = () => {
  showWinner.value = true;
};

const claimReward = () => {
  isOpen.value = false;
  emit('claimed');
};
</script>

<style scoped>
.roulette-wrapper {
  position: relative;
  width: 100%;
  height: 160px;
  background: #1e1e1e;
  border: 3px solid #333;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
}

.roulette-selector {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 4px;
  background: #ffb300;
  z-index: 10;
  transform: translateX(-50%);
  box-shadow: 0 0 10px #ffb300, 0 0 20px #ffb300;
}

.roulette-track {
  display: flex;
  height: 100%;
  width: max-content;
  align-items: center;
  will-change: transform;
}

.roulette-item {
  width: 140px;
  height: 130px;
  margin: 0 5px;
  background: #2a2a2a;
  border: 2px solid #444;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  flex-shrink: 0;
  padding: 8px;
}

.item-tier { font-size: 0.75rem; color: #999; letter-spacing: 1px; }
.item-name { margin-top: 4px; font-size: 0.9rem; line-height: 1.2; }

.winner-highlight {
  border-color: #4caf50;
  background: #1b5e20;
  box-shadow: 0 0 15px #4caf50;
  transform: scale(1.05);
  transition: all 0.5s ease;
  z-index: 5;
}
</style>