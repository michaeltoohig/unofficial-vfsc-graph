const nodeStatusColors = {
  'removed': '#dc3545',
  'liquidated': '#ffc107',
  'none': '#000000',
  'registered': '#42f54b'
};

const concentricLayoutOptions = {
  name: 'concentric',
  idealEdgeLength: 100,
  gravity: 0.65,
  nestingFactor: 0.25,
  concentric: function (node) {
    return node.degree();
  },
  levelWidth: function (nodes) {
    return 10;
  },
  animate: 'end',
  animationEasing: 'ease-out',
  animationDuration: 1000,
  nodeDimensionsIncludeLabels: true,
}

const bilkentLayoutOptions = {
  name: 'cose-bilkent',
  quality: 'proof',
  // animate: false,
  idealEdgeLength: 200,
  gravity: 0.64,
  nestingFactor: 0.25,
  //
  randomize: true,
  animate: 'end',
  animationEasing: 'ease-out',
  animationDuration: 1000,
  nodeDimensionsIncludeLabels: true
}

document.addEventListener('DOMContentLoaded', function () {
  const cy = cytoscape({
    container: document.getElementById('cy'),
    elements: graphData,
    // interaction elements
    zoomingEnabled: true,
    userZoomingEnabled: false,

    style: [
      {
        selector: 'node',
        style: {
          'background-color': '#666',
          'label': 'data(name)',
          'color': '#000',
          'font-size': '12px',
          'text-margin-y': '0px',
          'text-valign': 'center',
          'text-halign': 'center',
          "text-outline-width": 0.5,
          "text-outline-color": "#fff",
          'border-width': 2,
          'border-color': nodeStatusColors.none, // Default border color
        }
      },
      {
        selector: 'node[type="individual"]',
        style: {
          'shape': 'round-rectangle',
          'background-color': '#42f54b',
          'border-width': 0, // Remove border
        }
      },
      {
        selector: 'node[type="entity"][status="Removed"]',
        style: {
          'border-color': nodeStatusColors.removed,
        }
      },
      {
        selector: 'node[type="entity"][status="Dissolved"]',
        style: {
          'border-color': nodeStatusColors.removed,
        }
      },
      {
        selector: 'node[type="entity"][status="In Liquidation"]',
        style: {
          'border-color': nodeStatusColors.liquidated,
        }
      },
      {
        selector: 'node[type="entity"][status="Registered"]',
        style: {
          'border-color': nodeStatusColors.registered,
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': '#ccc',
          'target-arrow-color': '#ccc',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          // label
          'label': 'data(relationship)',
          'font-size': '6px',
          'text-rotation': 'autorotate',
          'text-margin-y': '-8px',
          'text-background-color': '#fff',
          'text-background-opacity': 0.7,
          'text-background-padding': '2px',
          'text-background-border': '2px'
        }
      },
      {
        selector: 'edge[relationship="director"]',
        style: {
          'width': 2,
          'line-color': '#bbb',
          'target-arrow-color': '#bbb',
        }
      }
    ],
    layout: bilkentLayoutOptions,
  })

  function setLayout(layoutName) {
    let layout;
    if (layoutName === 'concentric') {
      layout = cy.layout(concentricLayoutOptions);
    } else if (layoutName === 'cose-bilkent') {
      layout = cy.layout(bilkentLayoutOptions);
    }
    layout.run();
  }

  function filterRegisteredNodes(active) {
    if (active) {
      // Hide nodes not marked as "Registered"
      cy.nodes().forEach(function (node) {
        if (node.data('type') == 'entity' && node.data('status') !== 'Registered') {
          node.hide();
        }
      });

      // Hide edges missing one or both sides after nodes are hidden
      cy.edges().forEach(function (edge) {
        const targetNode = edge.target();
        const sourceNode = edge.source();

        if (!sourceNode || !targetNode) return;

        const isSourceRegistered = sourceNode.data('status') === 'Registered';
        const isTargetRegistered = targetNode.data('status') === 'Registered';
        const isSourceIndividual = sourceNode.data('type') === 'individual';
        const isTargetIndividual = targetNode.data('type') === 'individual';

        if (
          (isSourceRegistered || isTargetRegistered) ||
          (isSourceIndividual && isTargetRegistered) ||
          (isTargetIndividual && isSourceRegistered)
        ) {
          edge.show();
        } else {
          edge.hide();
        }
      });
    } else {
      // Show all nodes and edges
      cy.nodes().forEach(function (node) {
        node.show()
      });
      cy.edges().forEach(function (edge) {
        edge.show()
      });
    }

    // Apply changes
    setLayout('cose-bilkent');
  }

  // Set initial layout
  setLayout('cose-bilkent');

  // Add event listeners to layout buttons
  document.getElementById('concentricBtn').addEventListener('click', function () {
    setLayout('concentric');
  });
  document.getElementById('coseBilkentBtn').addEventListener('click', function () {
    setLayout('cose-bilkent');
  });

  // Add event listener to node filter switch
  document.getElementById('filterRegisteredSwitch').addEventListener('change', function (event) {
    const checked = event.target.checked;
    filterRegisteredNodes(checked);
  });

  // Node details card
  const nodeCard = document.getElementById('node-card');
  const nodeCardText = document.getElementById('node-card-text')
  const updateUrlBtn = document.getElementById('node-btn')
  let previouslySelectedNode = null;

  function updateCard(node) {
    const nodeId = node.id();
    nodeCard.dataset.nodeId = nodeId;
    nodeCardText.innerHTML = '';

    // Check and add name
    const nodeName = node.data('name');
    if (nodeName) {
      const nameLine = document.createElement('div');
      nameLine.textContent = `Name: ${nodeName}`;
      nodeCardText.appendChild(nameLine);
    }

    // Check and add status
    const nodeStatus = node.data('status');
    if (nodeStatus) {
      const statusLine = document.createElement('div');
      statusLine.textContent = `Status: ${nodeStatus}`;
      nodeCardText.appendChild(statusLine);
    }

    nodeCard.style.display = 'block';
  }

  // Update URL to selected node
  function constructNewUrl(nodeId) {
    const url = new URL(window.location.href);
    url.searchParams.set('nodeId', nodeId);
    return url.toString();
  }

  updateUrlBtn.addEventListener('click', function () {
    const nodeId = nodeCard.dataset.nodeId;
    if (nodeId) {
      const newUrl = constructNewUrl(nodeId);
      window.location.href = newUrl;
    }
  });

  function hideCard() {
    nodeCard.style.display = 'none';
  }

  cy.on('select', 'node', function (event) {
    const selectedNode = event.target;

    if (previouslySelectedNode) {
      previouslySelectedNode.removeStyle();
    }

    selectedNode.style({
      'overlay-opacity': 0.2,
      'overlay-color': '#000'
    });

    updateCard(selectedNode);
    previouslySelectedNode = selectedNode;
  });

  cy.on('unselect', 'node', function (event) {
    const unselectedNode = event.target;
    unselectedNode.removeStyle();
    hideCard();
    previouslySelectedNode = null;
  });

  // Zoom controls
  const zoomInBtn = document.getElementById('graph-zoom-in');
  zoomInBtn.addEventListener('click', function () {
    let zoomLevel = cy.zoom()
    cy.animate({
      zoom: {
        level: zoomLevel + 1,
        position: { x: 0, y: 0 },
      },
    }, {
      duation: 200,
    })
  })
  const zoomOutBtn = document.getElementById('graph-zoom-out');
  zoomOutBtn.addEventListener('click', function () {
    let zoomLevel = cy.zoom()
    cy.animate({
      zoom: {
        level: zoomLevel - 1,
        position: { x: 0, y: 0 },
      },
    }, {
      duation: 200,
    })
  })
  cy.on("dblclick", function (e) {
    let zoomLevel = cy.zoom()
    cy.animate({
      zoom: {
        level: zoomLevel + 1,
        renderedPosition: e.renderedPosition,
      },
    }, {
      duration: 200,
    })
  });
});

