// Grid-based layout function for tank upgrade trees
export function layoutGraphGrid(nodes, edges, options = {}) {
  const {
    gridSize = 150,           // Distance between grid positions
    nodeWidth = 120,          // Width of each node
    nodeHeight = 60,          // Height of each node
    startFromRoot = true,     // Whether to start layout from root nodes
    direction = 'LR'          // Layout direction: LR (left-right), TB (top-bottom)
  } = options;

  // Create adjacency lists for the graph
  const adjacencyList = new Map();
  const inDegree = new Map();
  const outDegree = new Map();

  // Initialize maps
  nodes.forEach(node => {
    adjacencyList.set(node.id, []);
    inDegree.set(node.id, 0);
    outDegree.set(node.id, 0);
  });

  // Build adjacency list and calculate degrees
  edges.forEach(edge => {
    adjacencyList.get(edge.source).push(edge.target);
    inDegree.set(edge.target, inDegree.get(edge.target) + 1);
    outDegree.set(edge.source, outDegree.get(edge.source) + 1);
  });

  // Find root nodes (nodes with no incoming edges)
  const rootNodes = nodes.filter(node => inDegree.get(node.id) === 0);

  // Find leaf nodes (nodes with no outgoing edges)
  const leafNodes = nodes.filter(node => outDegree.get(node.id) === 0);

  // If no clear roots, pick nodes with minimum in-degree
  const startNodes = rootNodes.length > 0 ? rootNodes :
    nodes.filter(node => inDegree.get(node.id) === Math.min(...Array.from(inDegree.values())));

  // Grid position tracking
  const gridPositions = new Map();
  const occupiedPositions = new Set();
  const nodePositions = new Map();

  // Helper function to get grid key
  const getGridKey = (x, y) => `${x},${y}`;

  // Helper function to check if position is available
  const isPositionAvailable = (x, y) => !occupiedPositions.has(getGridKey(x, y));

  // Helper function to find next available position in a direction
  const findNextAvailablePosition = (startX, startY, deltaX, deltaY) => {
    let x = startX + deltaX;
    let y = startY + deltaY;

    while (occupiedPositions.has(getGridKey(x, y))) {
      x += deltaX;
      y += deltaY;
    }

    return { x, y };
  };

  // BFS-based layout with grid constraints
  const layoutNodes = () => {
    const visited = new Set();
    const queue = [];

    // Start from root nodes, arrange them horizontally or vertically
    startNodes.forEach((node, index) => {
      let gridX, gridY;

      if (direction === 'LR') {
        gridX = 0;
        gridY = index * 2; // Space out root nodes vertically
      } else {
        gridX = index * 2; // Space out root nodes horizontally
        gridY = 0;
      }

      // Ensure position is available
      while (!isPositionAvailable(gridX, gridY)) {
        if (direction === 'LR') {
          gridY += 1;
        } else {
          gridX += 1;
        }
      }

      gridPositions.set(node.id, { x: gridX, y: gridY });
      occupiedPositions.add(getGridKey(gridX, gridY));
      queue.push(node.id);
      visited.add(node.id);
    });

    // Process queue for BFS layout
    while (queue.length > 0) {
      const currentNodeId = queue.shift();
      const currentPos = gridPositions.get(currentNodeId);
      const children = adjacencyList.get(currentNodeId) || [];

      children.forEach((childId, index) => {
        if (visited.has(childId)) return;

        let childGridX, childGridY;

        if (direction === 'LR') {
          // Place children to the right of parent
          const basePos = findNextAvailablePosition(
            currentPos.x,
            currentPos.y + (index - Math.floor(children.length / 2)),
            1, 0
          );
          childGridX = basePos.x;
          childGridY = basePos.y;
        } else {
          // Place children below parent
          const basePos = findNextAvailablePosition(
            currentPos.x + (index - Math.floor(children.length / 2)),
            currentPos.y,
            0, 1
          );
          childGridX = basePos.x;
          childGridY = basePos.y;
        }

        // Fine-tune position to avoid conflicts
        while (!isPositionAvailable(childGridX, childGridY)) {
          if (direction === 'LR') {
            childGridY += childGridY > currentPos.y ? 1 : -1;
          } else {
            childGridX += childGridX > currentPos.x ? 1 : -1;
          }
        }

        gridPositions.set(childId, { x: childGridX, y: childGridY });
        occupiedPositions.add(getGridKey(childGridX, childGridY));
        queue.push(childId);
        visited.add(childId);
      });
    }

    // Handle any remaining unvisited nodes
    nodes.forEach(node => {
      if (!visited.has(node.id)) {
        let gridX = 0, gridY = 0;

        // Find an available position
        while (!isPositionAvailable(gridX, gridY)) {
          if (direction === 'LR') {
            gridY++;
            if (gridY > 10) { // Prevent infinite loop
              gridX++;
              gridY = 0;
            }
          } else {
            gridX++;
            if (gridX > 10) { // Prevent infinite loop
              gridY++;
              gridX = 0;
            }
          }
        }

        gridPositions.set(node.id, { x: gridX, y: gridY });
        occupiedPositions.add(getGridKey(gridX, gridY));
      }
    });
  };

  // Execute layout
  layoutNodes();

  // Convert grid positions to pixel positions
  const laidOutNodes = nodes.map(node => {
    const gridPos = gridPositions.get(node.id);
    return {
      ...node,
      position: {
        x: gridPos.x * gridSize,
        y: gridPos.y * gridSize
      },
      style: {
        ...node.style,
        width: `${nodeWidth}px`,
        height: `${nodeHeight}px`,
      }
    };
  });

  // Create orthogonal edges (cardinal directions only)
  const laidOutEdges = edges.map((edge, index) => {
    const sourceNode = laidOutNodes.find(n => n.id === edge.source);
    const targetNode = laidOutNodes.find(n => n.id === edge.target);

    if (!sourceNode || !targetNode) return edge;

    // Calculate edge path for orthogonal routing
    const sourcePos = sourceNode.position;
    const targetPos = targetNode.position;

    // Determine if edge should be straight or have bends
    const isHorizontalAlign = Math.abs(sourcePos.y - targetPos.y) < gridSize / 4;
    const isVerticalAlign = Math.abs(sourcePos.x - targetPos.x) < gridSize / 4;

    let edgeStyle = {
      ...edge.style,
      stroke: edge.style?.stroke || '#64748b',
      strokeWidth: 2
    };

    // For orthogonal edges, we can use VueFlow's built-in smoothstep or step edge types
    return {
      ...edge,
      id: edge.id || `edge-${index}`,
      type: 'smoothstep', // or 'step' for sharp corners
      style: edgeStyle,
      labelStyle: {
        fontSize: '10px',
        fill: '#374151',
        background: 'white',
        padding: '2px 4px',
        borderRadius: '3px',
        ...edge.labelStyle
      }
    };
  });

  return {
    nodes: laidOutNodes,
    edges: laidOutEdges
  };
}

// Alternative simpler grid layout for more uniform spacing
export function layoutGraphSimpleGrid(nodes, edges, options = {}) {
  const {
    columns = Math.ceil(Math.sqrt(nodes.length)),
    gridSpacing = 150,
    nodeWidth = 120,
    nodeHeight = 60
  } = options;

  const laidOutNodes = nodes.map((node, index) => {
    const row = Math.floor(index / columns);
    const col = index % columns;

    return {
      ...node,
      position: {
        x: col * gridSpacing,
        y: row * gridSpacing
      },
      style: {
        ...node.style,
        width: `${nodeWidth}px`,
        height: `${nodeHeight}px`,
      }
    };
  });

  const laidOutEdges = edges.map((edge, index) => ({
    ...edge,
    id: edge.id || `edge-${index}`,
    type: 'smoothstep',
    style: {
      stroke: '#64748b',
      strokeWidth: 2,
      ...edge.style
    },
    labelStyle: {
      fontSize: '10px',
      fill: '#374151',
      background: 'white',
      padding: '2px 4px',
      borderRadius: '3px',
      ...edge.labelStyle
    }
  }));

  return {
    nodes: laidOutNodes,
    edges: laidOutEdges
  };
}