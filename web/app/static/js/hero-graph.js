document.addEventListener('DOMContentLoaded', function () {
  const nodeStatusColors = {
    'removed': '#dc3545',
    'liquidated': '#ffc107',
    'none': '#000000',
    'registered': '#42f54b'
  };

  const layoutOptions = {
    name: 'circle',
    quality: 'proof',
    idealEdgeLength: 64,
    gravity: 0.64,
    randomize: true,
    animate: 'end',
    animationEasing: 'ease-out',
    animationDuration: 1000,
    nodeDimensionsIncludeLabels: true
  };

  const cy = cytoscape({
    container: document.getElementById('cy'),
    elements: graphData,
    zoomingEnabled: true,
    userZoomingEnabled: false,
    // panningEnabled: false,
    userPanningEnabled: false,
    boxSelectionEnabled: false,
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
          'font-size': '8px',
          'text-rotation': 'autorotate',
          'text-margin-y': '-8px',
          'text-background-color': '#ccc',
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
    layout: layoutOptions,
  });

  // Function to continuously re-run the layout
  function animateGraph() {
    cy.layout(layoutOptions).run();
  }

  // Start the continuous animation
  animateGraph();
});
