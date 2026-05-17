// Inline icons rendered inside vis-network circularImage nodes.
//
// Tool icons live as .svg files COLOCATED with each tool's .py source
// (see user/<project>/tools/<source>.svg) and are served by the backend
// at /api/tools/{tool_name}/icon. Use api.getToolIconUrl(name) from useApi
// to get the URL; this module only provides:
//   - AGENT_ICON_PERSON  — embedded agent silhouette
//   - TOOL_ICON_FALLBACK — embedded gear, used as vis-network `brokenImage`
//                          when a tool has no .svg next to its .py
//
// Palette is aligned with GRAPH_COLORS (see graphColors.ts).

function svgDataUri(svg: string): string {
  const cleaned = svg.replace(/\s+/g, ' ').trim()
  return `data:image/svg+xml;utf8,${encodeURIComponent(cleaned)}`
}

const AGENT_BG = '#e8f7fc'
const AGENT_GLYPH = '#2d6d84'
const TOOL_BG = '#d6eef7'
const TOOL_GLYPH = '#2d6d84'
const TOOL_STROKE = '#0d3a4a'

const personBustSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="${AGENT_BG}"/>
  <g transform="translate(7.5 7.5) scale(0.85)">
    <circle cx="50" cy="38" r="17" fill="${AGENT_GLYPH}"/>
    <path d="M 14 100 Q 14 62 50 62 Q 86 62 86 100 Z" fill="${AGENT_GLYPH}"/>
  </g>
</svg>
`

const gearSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="${TOOL_BG}"/>
  <g transform="translate(7.5 7.5) scale(0.85)">
    <g fill="${TOOL_GLYPH}" stroke="${TOOL_STROKE}" stroke-width="3" stroke-linejoin="round">
      <circle cx="50" cy="50" r="22"/>
      <rect x="44" y="10" width="12" height="14"/>
      <rect x="44" y="76" width="12" height="14"/>
      <rect x="10" y="44" width="14" height="12"/>
      <rect x="76" y="44" width="14" height="12"/>
    </g>
    <circle cx="50" cy="50" r="8" fill="${TOOL_BG}" stroke="${TOOL_STROKE}" stroke-width="3"/>
  </g>
</svg>
`

export const AGENT_ICON_PERSON = svgDataUri(personBustSvg)
export const TOOL_ICON_FALLBACK = svgDataUri(gearSvg)
