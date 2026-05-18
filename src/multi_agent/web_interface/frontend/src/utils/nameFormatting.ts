/**
 * Converts a disk name (with underscores) to a display name (with spaces).
 * Example: "my_agent_name" -> "my agent name"
 */
export function toDisplayName(name: string | null | undefined): string {
  if (!name) return ''
  return String(name).replace(/_/g, ' ')
}

/**
 * Converts a display name (with spaces) to a disk name (with underscores).
 * Example: "my agent name" -> "my_agent_name"
 */
export function toDiskName(name: string | null | undefined): string {
  if (!name) return ''
  return String(name).replace(/\s+/g, '_')
}
