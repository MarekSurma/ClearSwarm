<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, onBeforeUpdate, nextTick, useAttrs } from 'vue'
import { AGENT_ICON_PERSON_INLINE, PROJECT_ICON_FOLDER_INLINE, TOOL_ICON_GEAR_INLINE } from '@/config/agentIcons'

defineOptions({
  inheritAttrs: false
})

const props = withDefaults(defineProps<{
  rows?: number
  placeholder?: string
  projects?: string[]
  agents?: string[]
  tools?: string[]
}>(), {
  rows: 3,
  placeholder: '',
  projects: () => [],
  agents: () => [],
  tools: () => []
})

const model = defineModel<string>({ required: true })

const agentIconUrl = AGENT_ICON_PERSON_INLINE
const projectIconUrl = PROJECT_ICON_FOLDER_INLINE
const toolIconUrl = TOOL_ICON_GEAR_INLINE

const emit = defineEmits<{
  'keydown.ctrl.enter': []
}>()

const textarea = ref<HTMLTextAreaElement | null>(null)
const backdropInner = ref<HTMLDivElement | null>(null)
const attrs = useAttrs()

const passThroughAttrs = computed(() => {
  const { class: _class, style: _style, ...rest } = attrs as Record<string, unknown>
  return rest
})

const showSuggestions = ref(false)
const suggestionTrigger = ref<'@' | '#' | '$' | null>(null)
const suggestionQuery = ref('')
const selectedSuggestionIndex = ref(0)
const suggestionPosition = ref({ top: 0, left: 0 })
const suggestionList = ref<HTMLDivElement | null>(null)
const suggestionItems = ref<HTMLLIElement[]>([])
const scrollOffset = ref({ top: 0, left: 0 })

onBeforeUpdate(() => {
  suggestionItems.value = []
})

function setSuggestionItemRef(el: Element | null, index: number) {
  if (el) suggestionItems.value[index] = el as HTMLLIElement
}

watch(selectedSuggestionIndex, () => {
  nextTick(() => {
    const activeItem = suggestionItems.value[selectedSuggestionIndex.value]
    if (activeItem && suggestionList.value) {
      const container = suggestionList.value
      const itemTop = activeItem.offsetTop
      const itemBottom = itemTop + activeItem.offsetHeight
      const containerTop = container.scrollTop
      const containerBottom = containerTop + container.offsetHeight

      if (itemTop < containerTop) {
        container.scrollTop = itemTop
      } else if (itemBottom > containerBottom) {
        container.scrollTop = itemBottom - container.offsetHeight
      }
    }
  })
})

function escapeRegex(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

const mentionRegex = computed(() => {
  // Longest first so alternation doesn't prefer shorter prefixes.
  const sortedAgents = [...props.agents].sort((a, b) => b.length - a.length).map(escapeRegex)
  const sortedProjects = [...props.projects].sort((a, b) => b.length - a.length).map(escapeRegex)
  const sortedTools = [...props.tools].sort((a, b) => b.length - a.length).map(escapeRegex)

  // Boundary on both sides:
  //   left  — only match when trigger is preceded by start-of-text or whitespace
  //           (so "user@agent" inside an email is not highlighted)
  //   right — name not followed by another word char, so "@agent_x" doesn't
  //           render as the shorter "@agent".
  const lead = '(?:^|(?<=\\s))'
  const agentRe = sortedAgents.length > 0 ? `${lead}(@)(${sortedAgents.join('|')})(?![\\w-])` : null
  const projectRe = sortedProjects.length > 0 ? `${lead}(#)(${sortedProjects.join('|')})(?![\\w-])` : null
  const toolRe = sortedTools.length > 0 ? `${lead}(\\$)(${sortedTools.join('|')})(?![\\w-])` : null

  const src = [agentRe, projectRe, toolRe].filter(Boolean).join('|')
  if (!src) return null
  return new RegExp(src, 'g')
})

type Part =
  | { kind: 'text'; text: string }
  | { kind: 'agent' | 'project' | 'tool'; trigger: string; name: string }

const highlightedParts = computed<Part[]>(() => {
  const text = model.value ?? ''
  if (!text) return []

  const regex = mentionRegex.value
  if (!regex) return [{ kind: 'text', text }]

  const parts: Part[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  regex.lastIndex = 0
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ kind: 'text', text: text.substring(lastIndex, match.index) })
    }
    // Agent group is 1+2, project 3+4, tool 5+6 (depending on which branch matched).
    const agentTrig = match[1]
    const agentName = match[2]
    const projTrig = match[3]
    const projName = match[4]
    const toolTrig = match[5]
    const toolName = match[6]
    if (agentTrig) {
      parts.push({ kind: 'agent', trigger: agentTrig, name: agentName })
    } else if (projTrig) {
      parts.push({ kind: 'project', trigger: projTrig, name: projName })
    } else if (toolTrig) {
      parts.push({ kind: 'tool', trigger: toolTrig, name: toolName })
    }
    lastIndex = regex.lastIndex
  }

  if (lastIndex < text.length) {
    parts.push({ kind: 'text', text: text.substring(lastIndex) })
  }

  return parts
})

function isBoundaryChar(ch: string | undefined) {
  return ch === undefined || ch === '' || /\s/.test(ch)
}

function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement
  const cursorPosition = target.selectionStart ?? 0
  const textBeforeCursor = target.value.substring(0, cursorPosition)

  const lastAt = textBeforeCursor.lastIndexOf('@')
  const lastHash = textBeforeCursor.lastIndexOf('#')
  const lastDollar = textBeforeCursor.lastIndexOf('$')
  const lastTriggerIndex = Math.max(lastAt, lastHash, lastDollar)

  if (lastTriggerIndex !== -1) {
    const charBefore = lastTriggerIndex === 0 ? '' : textBeforeCursor[lastTriggerIndex - 1]
    if (isBoundaryChar(charBefore)) {
      const trigger = textBeforeCursor[lastTriggerIndex] as '@' | '#' | '$'
      const query = textBeforeCursor.substring(lastTriggerIndex + 1)
      if (!query.includes(' ') && !query.includes('\n')) {
        suggestionTrigger.value = trigger
        suggestionQuery.value = query
        showSuggestions.value = true
        selectedSuggestionIndex.value = 0
        updateSuggestionPosition(target, lastTriggerIndex)
        return
      }
    }
  }

  showSuggestions.value = false
  suggestionTrigger.value = null
}

function getCaretCoordinates(el: HTMLTextAreaElement, position: number) {
  const style = window.getComputedStyle(el)
  const mirror = document.createElement('div')
  const copy = [
    'boxSizing', 'width', 'height',
    'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
    'fontFamily', 'fontSize', 'fontWeight', 'fontStyle', 'letterSpacing',
    'lineHeight', 'textTransform', 'wordSpacing', 'textIndent'
  ] as const
  for (const k of copy) {
    ;(mirror.style as any)[k] = (style as any)[k]
  }
  mirror.style.position = 'absolute'
  mirror.style.visibility = 'hidden'
  mirror.style.top = '0'
  mirror.style.left = '0'
  mirror.style.whiteSpace = 'pre-wrap'
  mirror.style.wordWrap = 'break-word'
  mirror.style.overflow = 'hidden'

  const before = el.value.substring(0, position)
  mirror.textContent = before
  const marker = document.createElement('span')
  marker.textContent = '​'
  mirror.appendChild(marker)

  el.parentElement?.appendChild(mirror)
  const top = marker.offsetTop
  const left = marker.offsetLeft
  const lineHeight = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.2
  mirror.remove()
  return { top, left, lineHeight }
}

function updateSuggestionPosition(el: HTMLTextAreaElement, triggerIndex: number) {
  const { top, left, lineHeight } = getCaretCoordinates(el, triggerIndex)
  suggestionPosition.value = {
    top: top + lineHeight - el.scrollTop,
    left: left - el.scrollLeft
  }
}

const filteredSuggestions = computed(() => {
  let list: string[]
  if (suggestionTrigger.value === '@') list = props.agents
  else if (suggestionTrigger.value === '#') list = props.projects
  else if (suggestionTrigger.value === '$') list = props.tools
  else list = []
  if (!suggestionQuery.value) return list
  const q = suggestionQuery.value.toLowerCase()
  return list.filter(item => item.toLowerCase().includes(q))
})

function selectSuggestion(suggestion: string) {
  if (!textarea.value || !suggestionTrigger.value) return

  const cursorPosition = textarea.value.selectionStart ?? 0
  const current = model.value ?? ''
  const textBeforeCursor = current.substring(0, cursorPosition)
  const textAfterCursor = current.substring(cursorPosition)

  const lastTriggerIndex = textBeforeCursor.lastIndexOf(suggestionTrigger.value)

  const newValue = textBeforeCursor.substring(0, lastTriggerIndex + 1) + suggestion + ' ' + textAfterCursor
  model.value = newValue

  showSuggestions.value = false
  suggestionTrigger.value = null

  nextTick(() => {
    const newCursorPos = lastTriggerIndex + 1 + suggestion.length + 1
    textarea.value?.setSelectionRange(newCursorPos, newCursorPos)
    textarea.value?.focus()
  })
}

function handleKeyDown(event: KeyboardEvent) {
  if (showSuggestions.value && filteredSuggestions.value.length > 0) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      selectedSuggestionIndex.value = (selectedSuggestionIndex.value + 1) % filteredSuggestions.value.length
      return
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      selectedSuggestionIndex.value = (selectedSuggestionIndex.value - 1 + filteredSuggestions.value.length) % filteredSuggestions.value.length
      return
    } else if (event.key === 'Enter' || event.key === 'Tab') {
      event.preventDefault()
      event.stopPropagation()
      selectSuggestion(filteredSuggestions.value[selectedSuggestionIndex.value])
      return
    } else if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      showSuggestions.value = false
      return
    }
  }

  if (event.ctrlKey && event.key === 'Enter') {
    event.preventDefault()
    emit('keydown.ctrl.enter')
  }
}

function syncScroll() {
  if (!textarea.value) return
  scrollOffset.value = {
    top: textarea.value.scrollTop,
    left: textarea.value.scrollLeft
  }
}

function handleBlur() {
  // Defer so a mousedown on a suggestion still fires selectSuggestion.
  setTimeout(() => {
    showSuggestions.value = false
  }, 100)
}

function handleDocumentMouseDown(event: MouseEvent) {
  if (!showSuggestions.value) return
  const target = event.target as Node
  if (textarea.value?.contains(target)) return
  if (suggestionList.value?.contains(target)) return
  showSuggestions.value = false
}

onMounted(() => {
  syncScroll()
  document.addEventListener('mousedown', handleDocumentMouseDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleDocumentMouseDown)
})
</script>

<template>
  <div class="mention-editor-container" :class="attrs.class as any" :style="attrs.style as any">
    <div class="mention-editor-backdrop">
      <div
        ref="backdropInner"
        class="mention-editor-backdrop-inner"
        :style="{ transform: `translate(${-scrollOffset.left}px, ${-scrollOffset.top}px)` }"
      >
        <template v-for="(part, i) in highlightedParts" :key="i"
          ><template v-if="part.kind === 'text'">{{ part.text }}</template
          ><span v-else-if="part.kind === 'agent'" class="mention-bold mention-agent"><span class="mention-trigger-slot"><span class="mention-trigger-hidden">{{ part.trigger }}</span><img class="mention-icon" :src="agentIconUrl" alt="" aria-hidden="true" /></span>{{ part.name }}</span
          ><span v-else-if="part.kind === 'project'" class="mention-bold mention-project"><span class="mention-trigger-slot"><span class="mention-trigger-hidden">{{ part.trigger }}</span><img class="mention-icon" :src="projectIconUrl" alt="" aria-hidden="true" /></span>{{ part.name }}</span
          ><span v-else class="mention-bold mention-tool"><span class="mention-trigger-slot"><span class="mention-trigger-hidden">{{ part.trigger }}</span><img class="mention-icon" :src="toolIconUrl" alt="" aria-hidden="true" /></span>{{ part.name }}</span
        ></template>
        <br v-if="(model ?? '').endsWith('\n')" />
      </div>
    </div>
    <textarea
      ref="textarea"
      v-bind="passThroughAttrs"
      v-model="model"
      class="mention-editor-textarea"
      :rows="rows"
      :placeholder="placeholder"
      @input="handleInput"
      @keydown="handleKeyDown"
      @scroll="syncScroll"
      @blur="handleBlur"
    ></textarea>

    <div
      v-if="showSuggestions && filteredSuggestions.length > 0"
      ref="suggestionList"
      class="mention-suggestions"
      :style="{ top: suggestionPosition.top + 'px', left: suggestionPosition.left + 'px' }"
    >
      <ul>
        <li
          v-for="(suggestion, index) in filteredSuggestions"
          :key="suggestion"
          :ref="el => setSuggestionItemRef(el, index)"
          :class="{ 'active': index === selectedSuggestionIndex }"
          @mousedown.prevent="selectSuggestion(suggestion)"
        >
          {{ suggestion }}
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.mention-editor-container {
  position: relative;
  width: 100%;
  font-family: inherit;
  border: 1px solid var(--p-content-border-color, #ccc);
  border-radius: var(--p-border-radius-md, 4px);
  background: var(--p-content-background, #fff);
  color: var(--p-text-color, #333);
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
  cursor: text;
}

.mention-editor-container:has(textarea:focus) {
  border-color: var(--p-primary-color, #3b82f6);
  outline: 0 none;
  box-shadow: 0 0 0 0.2rem var(--p-primary-100, rgba(59, 130, 246, 0.2));
}

.mention-editor-textarea,
.mention-editor-backdrop-inner {
  padding: 0.5rem 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  font-family: inherit;
  /* Force identical glyph metrics on both layers. Without these, browsers
     (and especially Firefox) can pick subtly different defaults for a
     textarea vs a div, drifting them out of column-for-column alignment. */
  font-weight: 400;
  font-style: normal;
  font-variant-ligatures: none;
  letter-spacing: 0;
  word-spacing: 0;
  text-indent: 0;
  text-transform: none;
  tab-size: 4;
  -moz-tab-size: 4;
  border: none;
  border-radius: inherit;
  box-sizing: border-box;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
  outline: none;
}

.mention-editor-textarea {
  position: relative;
  width: 100%;
  background: transparent;
  /* Hide rendered text in all browsers — only the caret should be visible;
     the colored backdrop layer below carries the legible text. Without the
     plain `color: transparent` Firefox renders the textarea's text on top
     of the backdrop, producing a "double text" effect. */
  color: transparent;
  -webkit-text-fill-color: transparent;
  caret-color: var(--p-text-color, #333);
  z-index: 2;
  display: block;
  overflow-y: auto;
  resize: none;
  cursor: text;
  /* Hide the native scrollbar. The backdrop layer is `overflow: hidden` (no
     scrollbar), so a visible scrollbar in the textarea would steal ~15px of
     content width — only on the textarea — which makes lines wrap earlier
     than the backdrop's lines. The user then sees ghost text at the end of
     a line (with spellcheck underlines): textarea cursor sits past where
     the backdrop renders text. Scrolling still works via wheel/keyboard. */
  scrollbar-width: none;
}

.mention-editor-textarea::-webkit-scrollbar {
  display: none;
}

/* Selection: paint only the highlight rectangle in the textarea; the
   textarea text itself stays transparent so it doesn't double up with the
   legible backdrop text underneath. The backdrop sits at a lower z-index
   so the highlight rectangle still shows on top of the visible text. */
.mention-editor-textarea::selection {
  background: var(--p-highlight-background, rgba(59, 130, 246, 0.35));
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.mention-editor-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  pointer-events: none;
  overflow: hidden;
  border-radius: inherit;
}

.mention-editor-backdrop-inner {
  width: 100%;
  color: var(--p-text-color, #333);
  will-change: transform;
}

.mention-bold {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  border-radius: 3px;
  white-space: nowrap;
  /* Extend the pill's painted background ~0.75em to the LEFT (into the
     whitespace that always precedes a mention — the regex enforces it) so
     the icon, which is shifted left to leave a ~5px gap before the name,
     visually sits inside the pill. The negative margin is balanced by the
     matching padding, so the laid-out slot+name positions are unchanged
     and the textarea/backdrop columns stay in sync. */
  margin-inline-start: -0.75em;
  padding-inline-start: 0.75em;
}

.mention-trigger-slot {
  position: relative;
  display: inline-block;
}

.mention-trigger-hidden {
  visibility: hidden;
}

.mention-icon {
  position: absolute;
  top: 50%;
  /* Anchor the icon's RIGHT edge ~3px (0.1875em) before the slot's right
     edge, which is where the agent/project name starts. This gives a clear
     visual gap between the icon and the name. The icon then overflows to
     the LEFT into the pill's extended padding (see .mention-bold above),
     so it still reads as part of the same pill. The translateY also nudges
     the icon up by 2px for better optical centering against the text. */
  right: 0.0625em;
  transform: translateY(calc(-50% - 2px));
  width: 1em;
  height: 1em;
  pointer-events: none;
  user-select: none;
}

.mention-suggestions {
  position: absolute;
  z-index: 1000;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  min-width: 150px;
  max-height: 200px;
  overflow-y: auto;
}

.mention-suggestions ul {
  list-style: none;
  padding: 0.25rem 0;
  margin: 0;
}

.mention-suggestions li {
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-size: 0.9rem;
}

.mention-suggestions li.active,
.mention-suggestions li:hover {
  background: var(--p-content-hover-background);
  color: var(--p-content-hover-color);
}
</style>
