/**
 * Shared color palette for all vis-network graph views
 * Organic blue theme — aligned with PrimeVue Organic preset
 */

export const GRAPH_COLORS = {
  // Font colors
  font: {
    primary: '#c8dde8',
    face: 'monospace',
  },

  // Background color
  background: 'rgb(61, 148, 181)',

  // Editor graph (agent editor) — edge colors
  editor: {
    edges: {
      default: '#82dbff',
      highlight: '#a0e5ff',
      hover: '#a0e5ff',
    },
  },

  // Visualizer graph (run visualizer)
  visualizer: {
    edges: {
      default: '#82dbff',
      highlight: '#a0e5ff',
      hover: '#a0e5ff',
      async: '#3e5f6e',
      asyncHighlight: '#82c4d9',
    },
    borders: {
      default: '#82dbff',
      highlight: '#a0e5ff',
    },
    root: {
      background: '#4bb7df',
      backgroundRunning: '#6dc9e8',
      backgroundError: '#e57373',
      font: '#352020',
      size: 30,
    },
    agent: {
      background: '#2d6d84',
      backgroundRunning: '#3d8da4',
      backgroundError: '#d32f2f',
      font: '#aee8ff',
      size: 20,
    },
    tool: {
      background: '#2d6d84',
      backgroundRunning: '#3d8da4',
      font: '#aee8ff',
      size: 15,
    },
  },

  // Shadow colors
  shadows: {
    default: 'rgba(61, 148, 181, 0.3)',
    defaultSize: 12,
  },

  // Agent node colors
  agent: {
    background: '#4bb7df',
    border: '#82dbff',
    highlightBackground: '#6dc9e8',
    highlightBorder: '#a0e5ff',
    shadow: 'rgba(61, 148, 181, 0.4)',
    shadowSize: 12,
    rootShadow: 'rgba(90, 173, 201, 0.5)',
    rootShadowSize: 18,
    font: '#352020',
  },

  // Tool node colors
  tool: {
    background: '#2d6d84',
    border: '#82dbff',
    highlightBackground: '#3d8da4',
    highlightBorder: '#a0e5ff',
    shadow: 'rgba(38, 97, 123, 0.35)',
    shadowSize: 10,
    font: '#aee8ff',
  },

  // Running state colors
  running: {
    generating: {
      border: '#5aadc9',
      shadow: 'rgba(90, 173, 201, 0.7)',
    },
    waiting: {
      border: '#3e5f6e',
      shadow: 'rgba(62, 95, 110, 0.6)',
    },
    executingTool: {
      border: '#82c4d9',
      shadow: 'rgba(130, 196, 217, 0.7)',
    },
    default: {
      border: '#b3dbe9',
      shadow: 'rgba(179, 219, 233, 0.5)',
    },
  },

  // Error state colors
  error: {
    border: '#c03030',
    borderRunning: '#d04030',
    shadow: 'rgba(192, 48, 48, 0.6)',
    shadowRunning: 'rgba(208, 64, 48, 0.7)',
    shadowSize: 18,
  },
} as const
