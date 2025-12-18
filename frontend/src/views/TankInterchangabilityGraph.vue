<template>
  <div class="app-container">
    <div class="controls-panel">
      <v-text-field
        v-model="searchQuery"
        label="Search for a tank..."
        prepend-inner-icon="mdi-magnify"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        style="max-width: 400px;"
      />

      <v-btn
        icon="mdi-refresh"
        variant="text"
        @click="loadAllData"
        :loading="loading"
        class="ml-2"
        color="primary"
      />

      <v-spacer />

      <div class="text-caption text-medium-emphasis">
        Showing {{ filteredChains.length }} chains
      </div>
    </div>

    <div class="chains-wrapper pa-4">

      <div v-if="loading" class="d-flex justify-center mt-10">
        <v-progress-circular indeterminate color="primary" size="64" />
      </div>

      <div v-else-if="!filteredChains.length" class="text-center mt-10 text-grey">
        No interchange chains found.
      </div>

      <div v-else class="chains-container">
        <v-card
          v-for="(chain, idx) in filteredChains"
          :key="idx"
          class="mb-3 chain-card"
          elevation="1"
          border
        >
          <v-card-text class="d-flex align-center flex-wrap py-3 px-4">
            <template v-for="(segment, sIdx) in chain" :key="sIdx">

              <v-chip
                :color="getTankColor(segment.tank, searchQuery)"
                :variant="isMatch(segment.tank, searchQuery) ? 'flat' : 'tonal'"
                label
                size="default"
                class="font-weight-medium"
                style="min-width: 120px; justify-content: center;"
              >
                {{ segment.tank }}
              </v-chip>

              <div v-if="segment.nextArrow" class="mx-2 d-flex flex-column align-center connector" style="width: 40px;">
                <v-icon
                  :icon="getArrowIcon(segment.nextArrow)"
                  color="grey"
                  size="small"
                />
                <span v-if="segment.nextCost" class="text-caption font-weight-bold text-success" style="font-size: 0.7rem;">
                  {{ segment.nextCost }}
                </span>
              </div>

            </template>
          </v-card-text>
        </v-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useUserStore } from "@/config/store.ts"

const $cookies = inject("$cookies")
const csrfToken = $cookies.get('csrftoken')
const userStore = useUserStore()

const loading = ref(false)
const searchQuery = ref('')
const allChains = ref([]) // Stores the processed linear chains

// --- 1. Linearizer Algorithm (Transforms Edges -> Rows) ---
const buildChains = (edges) => {
  if (!edges || edges.length === 0) return []

  // Step A: Build Adjacency List
  const adj = {}
  const allNodes = new Set()

  edges.forEach(e => {
    allNodes.add(e.from_tank)
    allNodes.add(e.to_tank)

    if (!adj[e.from_tank]) adj[e.from_tank] = []
    if (!adj[e.to_tank]) adj[e.to_tank] = []

    adj[e.from_tank].push({
      target: e.to_tank,
      type: e.is_bidirectional ? 'bi' : 'out',
      cost: e.cost,
      id: `${e.from_tank}|${e.to_tank}`
    })

    // Add reverse mapping for graph traversal, even if one-way
    adj[e.to_tank].push({
      target: e.from_tank,
      type: e.is_bidirectional ? 'bi' : 'in',
      cost: e.cost,
      id: `${e.from_tank}|${e.to_tank}`
    })
  })

  const visitedEdges = new Set()
  const resultChains = []

  // Step B: Find "Start" nodes (Leaves or sources)
  // We sort nodes by degree (connections count) ascending, so we start at ends of chains
  const sortedNodes = Array.from(allNodes).sort((a, b) => {
    return (adj[a]?.length || 0) - (adj[b]?.length || 0)
  })

  // Step C: Traverse
  sortedNodes.forEach(startNode => {
    // If this node has any unvisited edges, start a new chain here
    if (!adj[startNode].some(edge => !visitedEdges.has(edge.id))) return

    let currentChain = [{ tank: startNode }]
    let currentNode = startNode
    let walking = true

    while (walking) {
      // Find valid neighbors (unvisited edges)
      // Prefer 'out' or 'bi' direction for visual flow
      let neighbors = adj[currentNode].filter(e => !visitedEdges.has(e.id))

      if (neighbors.length === 0) {
        walking = false
        break
      }

      // Pick best neighbor (Simple heuristic: take first one found)
      let nextStep = neighbors[0]
      visitedEdges.add(nextStep.id)

      // Determine visual arrow
      let arrow = 'right'
      if (nextStep.type === 'bi') arrow = 'bi'
      else if (nextStep.type === 'in') arrow = 'left'

      // Update previous node with arrow info
      currentChain[currentChain.length - 1].nextArrow = arrow
      currentChain[currentChain.length - 1].nextCost = nextStep.cost > 0 ? nextStep.cost : null

      // Move forward
      currentNode = nextStep.target
      currentChain.push({ tank: currentNode })
    }

    if (currentChain.length > 1) {
      resultChains.push(currentChain)
    }
  })

  return resultChains
}

// --- 2. API & Data Loading ---
const loadAllData = async () => {
  loading.value = true
  try {
    // No headers means "Get All" per our backend change
    const res = await fetch(`/api/league/interchanges/`, {
      headers: {
        'X-CSRFToken': csrfToken,
        'team': userStore.team
      }
    })

    if (res.ok) {
      const edges = await res.json()
      // Process the massive edge list into neat rows
      allChains.value = buildChains(edges)
    }
  } catch (err) {
    console.error("Failed to load interchanges", err)
  } finally {
    loading.value = false
  }
}

// --- 3. Filtering & Visuals ---
const filteredChains = computed(() => {
  if (!searchQuery.value) return allChains.value

  const q = searchQuery.value.toLowerCase()
  return allChains.value.filter(chain =>
    chain.some(segment => segment.tank.toLowerCase().includes(q))
  )
})

const isMatch = (tankName, query) => {
  if (!query) return false
  return tankName.toLowerCase().includes(query.toLowerCase())
}

const getTankColor = (name, query) => {
  if (isMatch(name, query)) return 'primary'
  if (name.includes('**')) return 'amber-darken-4' // Highlight special/premium if denoted by **
  return 'surface-variant'
}

const getArrowIcon = (type) => {
  if (type === 'bi') return 'mdi-arrow-left-right'
  if (type === 'left') return 'mdi-arrow-left'
  return 'mdi-arrow-right'
}

// --- 4. Init ---
onMounted(() => {
  loadAllData()
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: rgb(var(--v-theme-background));
}

.controls-panel {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background-color: rgb(var(--v-theme-surface));
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
  gap: 12px;
}

.chains-wrapper {
  flex: 1;
  overflow-y: auto;
}
</style>