<script setup lang="ts">
import { onMounted } from 'vue'
import AppNav from '@/components/common/AppNav.vue'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import { useProject } from '@/composables/useProject'

const { loadProjects } = useProject()

// Load projects on mount
onMounted(async () => {
  await loadProjects()
})
</script>

<template>
  <div class="app-layout">
    <AppNav />
    <main class="app-main">
      <router-view />
    </main>
    <Toast position="top-right" />
    <ConfirmDialog />
  </div>
</template>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-family: 'Inter', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  min-height: 100vh;
}

.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-main {
  flex: 1;
  padding: 1.5rem;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--p-surface-100);
}

::-webkit-scrollbar-thumb {
  background: var(--p-surface-400);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--p-surface-500);
}

/* Utility for monospace text */
.mono {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.875rem;
}
</style>
