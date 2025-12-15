<template>
  <div class="app-container">
    <div class="controls-panel">
      <v-btn-toggle v-model="layoutType" mandatory>
        <v-btn value="hierarchical">Hierarchical Grid</v-btn>
        <v-btn value="grid">Simple Grid</v-btn>
        <v-btn value="dagre">Dagre</v-btn>
      </v-btn-toggle>

      <v-btn @click="refreshLayout" class="ml-4">
        <v-icon>mdi-refresh</v-icon>
        Refresh Layout
      </v-btn>

      <v-btn @click="fitToView" class="ml-4">
        <v-icon>mdi-fit-to-page</v-icon>
        Fit View
      </v-btn>

      <v-autocomplete
        class="ml-4"
        v-model="selectedTree"
        :items="upgradeTrees"
        item-title="label"
        item-value="value"
        label="Select Upgrade Tree"
        density="compact"
        chips
        clearable
        style="height: 48px; margin-top: 8px;"
      />
    </div>

    <div class="cytoscape-wrapper">
      <div ref="cytoscapeContainer" class="cytoscape-container"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, inject, watch, nextTick, computed } from 'vue'
import { useUserStore } from "@/config/store.ts"
import { useTheme } from 'vuetify'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'

const $cookies = inject("$cookies")
const csrfToken = $cookies.get('csrftoken')
const userStore = useUserStore()
const theme = useTheme()

// Register extensions
cytoscape.use(dagre)

const cytoscapeContainer = ref(null)
const layoutType = ref('dagre')
const nodeCount = ref(0)
const edgeCount = ref(0)
const rawData = ref([])
let cy = null
const savedTree = localStorage.getItem('selectedTree')
const selectedTree = ref(savedTree || 'M4')
const upgradeTrees = ref([])

const cytoscapeStyles = computed(() => {
  const isDark = theme.global.current.value.dark

  return [
    {
      selector: 'node',
      style: {
        'background-color': isDark ? '#1e293b' : '#e0f2fe',
        'border-color': isDark ? '#3b82f6' : '#0369a1',
        'border-width': 2,
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'color': isDark ? '#e2e8f0' : '#1e40af',
        'font-size': '16px',
        'font-weight': 'bold',
        'width': 200,
        'height': 60,
        'shape': 'round-rectangle'
      }
    },
    {
      selector: 'node:selected',
      style: {
        'background-color': isDark ? '#334155' : '#bfdbfe',
        'border-color': isDark ? '#60a5fa' : '#1d4ed8',
        'border-width': 3
      }
    },
    {
      selector: 'node:hover',
      style: {
        'background-color': isDark ? '#475569' : '#dbeafe',
        'border-color': isDark ? '#93c5fd' : '#2563eb'
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': isDark ? '#22c55e' : '#10b981',
        'target-arrow-color': isDark ? '#22c55e' : '#10b981',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'label': 'data(label)',
        'font-size': '14px',
        'color': isDark ? '#cbd5e1' : '#374151',
        'text-background-color': isDark ? '#0f172a' : '#ffffff',
        'text-background-opacity': 0.8,
        'text-background-padding': '2px'
      }
    },
    {
      selector: 'edge.unavailable',
      style: {
        'line-color': isDark ? '#f87171' : '#ef4444',
        'target-arrow-color': isDark ? '#f87171' : '#ef4444',
        'line-style': 'dashed'
      }
    },
    {
      selector: 'edge:hover',
      style: {
        'width': 3,
        'line-color': isDark ? '#4ade80' : '#059669',
        'target-arrow-color': isDark ? '#4ade80' : '#059669'
      }
    }
  ]
})

// Enhanced hierarchical tree layout function
const hierarchicalGridLayout = (cyInstance) => {
  const nodes = cyInstance.nodes()
  const edges = cyInstance.edges()

  // Build adjacency lists and degree tracking
  const children = new Map()
  const parents = new Map()
  const inDegree = new Map()
  const outDegree = new Map()
  const nodeById = new Map()

  nodes.forEach(node => {
    const id = node.id()
    children.set(id, [])
    parents.set(id, [])
    inDegree.set(id, 0)
    outDegree.set(id, 0)
    nodeById.set(id, node)
  })

  edges.forEach(edge => {
    const source = edge.source().id()
    const target = edge.target().id()
    children.get(source).push(target)
    parents.get(target).push(source)
    inDegree.set(target, inDegree.get(target) + 1)
    outDegree.set(source, outDegree.get(source) + 1)
  })

  // Find root nodes (starting tanks - no incoming edges)
  const rootNodes = nodes.filter(node => inDegree.get(node.id()) === 0)

  console.log('Root nodes found:', rootNodes.map(n => n.id()))

  // Calculate tree structure with proper branching
  const nodePositions = new Map()
  const levelNodes = new Map() // level -> nodes at that level
  const nodeLevel = new Map() // node -> its level

  // BFS to assign levels and track tree structure
  const visited = new Set()
  let queue = rootNodes.map(node => ({ node, level: 0, parentX: 0 }))

  while (queue.length > 0) {
    const { node, level, parentX } = queue.shift()
    const nodeId = node.id()

    if (visited.has(nodeId)) continue
    visited.add(nodeId)

    // Track level assignment
    nodeLevel.set(nodeId, level)
    if (!levelNodes.has(level)) {
      levelNodes.set(level, [])
    }
    levelNodes.get(level).push({ node, parentX })

    // Add children to queue
    const nodeChildren = children.get(nodeId) || []
    nodeChildren.forEach(childId => {
      if (!visited.has(childId)) {
        const childNode = nodeById.get(childId)
        if (childNode) {
          queue.push({ node: childNode, level: level + 1, parentX })
        }
      }
    })
  }

  // Position calculation with proper tree spacing
  const horizontalSpacing = 500
  const verticalSpacing = 200
  const positions = new Map()

  // Process each level
  const maxLevel = Math.max(...levelNodes.keys())

  for (let level = 0; level <= maxLevel; level++) {
    const nodesAtLevel = levelNodes.get(level) || []

    if (level === 0) {
      // Root level - center the root nodes
      nodesAtLevel.forEach((item, index) => {
        const x = (index - (nodesAtLevel.length - 1) / 2) * horizontalSpacing * 2
        const y = 0
        positions.set(item.node.id(), { x, y })
      })
    } else {
      // Child levels - position based on parent and siblings
      const levelGroups = new Map() // Group nodes by their parent

      nodesAtLevel.forEach(item => {
        const nodeParents = parents.get(item.node.id()) || []
        const parentId = nodeParents[0] // Take first parent for positioning

        if (!levelGroups.has(parentId)) {
          levelGroups.set(parentId, [])
        }
        levelGroups.get(parentId).push(item.node)
      })

      // Position each group under its parent
      let currentOffset = 0
      levelGroups.forEach((siblings, parentId) => {
        const parentPos = positions.get(parentId)
        const parentX = parentPos ? parentPos.x : 0

        // Calculate spacing for this group
        const groupWidth = (siblings.length - 1) * horizontalSpacing
        const startX = parentX - groupWidth / 2

        siblings.forEach((node, index) => {
          const x = startX + index * horizontalSpacing
          const y = level * verticalSpacing
          positions.set(node.id(), { x, y })
        })
      })
    }
  }

  // Apply positions to nodes
  positions.forEach((pos, nodeId) => {
    const node = nodeById.get(nodeId)
    if (node) {
      node.position(pos)
    }
  })

  console.log('Positioned', positions.size, 'nodes across', maxLevel + 1, 'levels')

  return {
    name: 'preset',
    positions: (node) => positions.get(node.id()) || { x: 0, y: 0 }
  }
}

// Update styles when theme changes
const updateCytoscapeStyles = () => {
  if (!cy) return

  cy.style(cytoscapeStyles.value)
  cy.forceRender()
}

// Initialize Cytoscape
const initCytoscape = () => {
  if (!cytoscapeContainer.value) return

  cy = cytoscape({
    container: cytoscapeContainer.value,

    elements: [],

    style: cytoscapeStyles.value,

    layout: { name: 'grid' },

    zoomingEnabled: true,
    userZoomingEnabled: true,
    panningEnabled: true,
    userPanningEnabled: true,
    boxSelectionEnabled: true,
    selectionType: 'single',

    motionBlur: false,
    wheelSensitivity: 2,
    minZoom: 0.1,
    maxZoom: 3
  })

  // Add event listeners
  cy.on('tap', 'node', (evt) => {
    const node = evt.target
    console.log('Node clicked:', node.data())
  })

  console.log('Cytoscape initialized')
}

// Apply layout
const applyLayout = () => {
  if (!cy) return

  let layoutOptions

  switch (layoutType.value) {
    case 'hierarchical':
      layoutOptions = hierarchicalGridLayout(cy)
      break
    case 'grid':
      layoutOptions = {
        name: 'grid',
        rows: Math.ceil(Math.sqrt(cy.nodes().length)),
        cols: undefined,
        position: (node) => ({ row: undefined, col: undefined }),
        sort: undefined,
        animate: true,
        animationDuration: 500,
        fit: true,
        padding: 50,
        spacingFactor: 1.5
      }
      break
    case 'dagre':
      layoutOptions = {
        name: 'dagre',
        nodeSep: 100,
        edgeSep: 10,
        rankSep: 150,
        rankDir: 'TB',
        align: undefined,
        acyclicer: 'greedy',
        ranker: 'network-simplex',
        animate: true,
        animationDuration: 500,
        fit: true,
        padding: 50
      }
      break
    case 'breadthfirst':
      layoutOptions = {
        name: 'breadthfirst',
        directed: true,
        roots: cy.nodes('[indegree = 0]'),
        padding: 50,
        spacingFactor: 1.5,
        animate: true,
        animationDuration: 500,
        fit: true
      }
      break
    default:
      layoutOptions = { name: 'grid' }
  }

  const layout = cy.layout(layoutOptions)
  layout.run()

  console.log('Layout applied:', layoutType.value)
}

// Load data into Cytoscape with edge filtering
const loadData = () => {
  if (!cy || !rawData.value.length) {
    console.log('No cy instance or data')
    return
  }

  // Extract unique tanks
  const tankSet = new Set()
  rawData.value.forEach(upg => {
    tankSet.add(upg.from_tank)
    tankSet.add(upg.to_tank)
  })

  // Filter out bidirectional edges - keep only one direction
  const edgeMap = new Map()
  const filteredUpgrades = []

  rawData.value.forEach(upg => {
    const forward = `${upg.from_tank}->${upg.to_tank}`
    const reverse = `${upg.to_tank}->${upg.from_tank}`

    // If we haven't seen either direction, add this one
    if (!edgeMap.has(forward) && !edgeMap.has(reverse)) {
      edgeMap.set(forward, upg)
      filteredUpgrades.push(upg)
    }
    // If we've seen the reverse, decide which one to keep based on some criteria
    else if (edgeMap.has(reverse)) {
      const existingUpgrade = edgeMap.get(reverse)

      // Keep the one with lower cost or tier (assuming forward progression)
      // Or use alphabetical order, or prefer available ones
      const shouldReplace =
        upg.cost > existingUpgrade.cost ||
        upg.required_kit_tier > existingUpgrade.required_kit_tier

      if (shouldReplace) {
        // Remove the reverse entry and add forward
        edgeMap.delete(reverse)
        edgeMap.set(forward, upg)

        // Replace in filtered array
        const reverseIndex = filteredUpgrades.findIndex(u =>
          u.from_tank === existingUpgrade.from_tank &&
          u.to_tank === existingUpgrade.to_tank
        )
        if (reverseIndex !== -1) {
          filteredUpgrades[reverseIndex] = upg
        }
      }
    }
  })

  console.log('Original edges:', rawData.value.length, 'Filtered edges:', filteredUpgrades.length)

  // Create nodes
  const nodes = [...tankSet].map(tank => ({
    data: {
      id: tank,
      label: tank
    }
  }))

  // Create edges from filtered data
  const edges = filteredUpgrades.map((upg, idx) => ({
    data: {
      id: `e-${idx}`,
      source: upg.from_tank,
      target: upg.to_tank,
      label: `${upg.cost} | ${upg.required_kit_tier ? upg.required_kit_tier : 'P'}`
    }
  }))

  console.log('Loading data - Nodes:', nodes.length, 'Edges:', edges.length)

  cy.elements().remove()
  cy.add([...nodes, ...edges])

  nodeCount.value = nodes.length
  edgeCount.value = edges.length

  // Apply layout after data is loaded
  setTimeout(() => {
    applyLayout()
  }, 100)
}

// Utility functions
const refreshLayout = () => {
  applyLayout()
}

const fitToView = () => {
  if (cy) {
    cy.fit(null, 50)
  }
}

// Watchers
watch(layoutType, () => {
  applyLayout()
})

watch(selectedTree, (newVal) => {
  if (newVal) {
    localStorage.setItem('selectedTree', newVal)
    loadApiData()
  } else {
    rawData.value = []
    if (cy) cy.elements().remove()
  }
})


// Watch for theme changes and update styles
watch(() => theme.global.current.value.dark, () => {
  updateCytoscapeStyles()
}, { immediate: false })

// Lifecycle
onMounted(async () => {
  console.log('Component mounted')

  // Wait for DOM
  await nextTick()
  await loadUpgradeTrees()
  initCytoscape()
  await loadApiData()
})

const loadUpgradeTrees = async () => {
  try {
    const res = await fetch('/api/league/upgrades/labels/', {
      method: 'GET',
      headers: { 'X-CSRFToken': csrfToken }
    })
    if (res.ok) {
      upgradeTrees.value = await res.json()
    }
  } catch (err) {
    console.error('Error loading upgrade trees:', err)
  }
}

const loadApiData = async () => {

  try {
    const res = await fetch(`/api/league/upgrades/`, {
      method: 'GET',
      headers: {
        'X-CSRFToken': csrfToken,
        'team': userStore.team,
        'tank': selectedTree.value
      }
    })

    if (res.ok) {
      const data = await res.json()
      console.log('API data received:', data)
      rawData.value = data.filter(upg => upg.in_graph === true)
      console.log('Filtered data:', rawData.value)
      loadData()
    }

  } catch (error) {
    console.error('API error:', error)
  }
}

onUnmounted(() => {
  if (cy) {
    cy.destroy()
  }
})
</script>

<style scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.controls-panel {
  padding: 16px;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  flex-wrap: wrap;
  max-height: 15vh;
}

.cytoscape-wrapper {
  flex: 1;
  position: relative;
  min-height: 0;
  max-height: 85vh;
  padding: 0 16px 0 16px;
}

.cytoscape-container {
  width: 100%;
  height: 100%;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgb(var(--v-theme-surface-variant));
}
</style>