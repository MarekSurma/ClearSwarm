<script setup lang="ts">
import { useRoute } from 'vue-router'
import Menubar from 'primevue/menubar'

const route = useRoute()
</script>

<template>
  <nav class="app-nav">
    <div class="nav-inner">
      <router-link to="/" class="nav-brand">
        <img src="@/assets/favicon.svg" alt="ClearSwarm" class="nav-logo" />
        <span class="nav-brand-text">ClearSwarm</span>
      </router-link>
      <div class="nav-links">
        <router-link
          to="/"
          class="nav-link"
          :class="{ active: route.name === 'runner' }"
        >
          <i class="pi pi-play" />
          Runner
        </router-link>
        <router-link
          to="/editor"
          class="nav-link"
          :class="{ active: route.name === 'editor' }"
        >
          <i class="pi pi-pencil" />
          Editor
        </router-link>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.app-nav {
  border-bottom: 1px solid var(--p-surface-200);
  padding: 0 1.5rem;
}

.nav-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1600px;
  margin: 0 auto;
  height: 56px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: var(--p-text-color);
  font-weight: 600;
  font-size: 1.1rem;
}

.nav-logo {
  width: 28px;
  height: 28px;
}

.nav-links {
  display: flex;
  gap: 0.25rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  text-decoration: none;
  color: var(--p-text-muted-color);
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.15s ease;
}

.nav-link:hover {
  color: var(--p-text-color);
  background: var(--p-surface-100);
}

.nav-link.active {
  color: var(--p-primary-color);
  background: var(--p-primary-50);
}
</style>
