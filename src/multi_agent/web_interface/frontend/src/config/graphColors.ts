/**
 * Shared color palette for all vis-network graph views
 * Based on the ClearSwarm visualizer warm brown/orange theme
 */

export const GRAPH_COLORS = {
  // Font colors
  font: {
    primary: '#e0c8a8',
    face: 'monospace',
  },

  // Background color
  background: '#0a0a0a',

  // Edge colors
  edges: {
    default: '#5a3a28',
    highlight: '#8a6048',
    hover: '#8a6048',
    async: '#7a5840',
    asyncHighlight: '#a07858',
  },

  // Node border colors
  borders: {
    default: '#6b4030',
    highlight: '#f0d8b0',
  },

  // Shadow colors
  shadows: {
    default: 'rgba(180, 100, 50, 0.35)',
    defaultSize: 12,
  },

  // Agent node colors
  agent: {
    background: '#e89030',
    border: '#c07020',
    highlightBackground: '#f0a040',
    highlightBorder: '#d08030',
    shadow: 'rgba(232, 144, 48, 0.35)',
    shadowSize: 12,
    rootShadow: 'rgba(232, 144, 48, 0.5)',
    rootShadowSize: 18,
  },

  // Tool node colors (matching the warm palette)
  tool: {
    background: '#a88050',
    border: '#886840',
    highlightBackground: '#c89860',
    highlightBorder: '#a88050',
    shadow: 'rgba(168, 128, 80, 0.35)',
    shadowSize: 10,
  },

  // Running state colors
  running: {
    generating: {
      border: '#e89030',
      shadow: 'rgba(232, 144, 48, 0.7)',
    },
    waiting: {
      border: '#a06850',
      shadow: 'rgba(160, 104, 80, 0.6)',
    },
    executingTool: {
      border: '#c89838',
      shadow: 'rgba(200, 152, 56, 0.7)',
    },
    default: {
      border: '#d0b880',
      shadow: 'rgba(208, 184, 128, 0.6)',
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
