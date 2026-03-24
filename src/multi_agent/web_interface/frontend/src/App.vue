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
  background-color: var(--p-surface-50);
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

/* Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--p-surface-200);
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--p-surface-300);
}

/* Utility for monospace text */
.mono {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.875rem;
}
</style>
