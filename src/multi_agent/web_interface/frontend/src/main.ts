import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import { definePreset } from '@primevue/themes'
import Lara from '@primevue/themes/lara'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'

const Organic = definePreset(Lara, {
  semantic: {
    primary: {
      50:  '#e0f2f2',
      100: '#b3e0e0',
      200: '#80cccc',
      300: '#5bb2b2',
      400: '#3a9999',
      500: '#2d7a7a',
      600: '#236060',
      700: '#1a4848',
      800: '#123434',
      900: '#0a2020',
      950: '#051414',
    },
    colorScheme: {
      light: {
        primary: {
          color: '#5bb2b2',
          contrastColor: '#ffffff',
          hoverColor: '{primary.400}',
          activeColor: '{primary.500}',
        },
        highlight: {
          background: '{primary.50}',
          focusBackground: '{primary.100}',
          color: '{primary.500}',
          focusColor: '{primary.600}',
        },
        surface: {
          0:   '#ffffff',
          50:  '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
      },
      dark: {
        primary: {
          color: '{primary.300}',
          contrastColor: '{surface.900}',
          hoverColor: '{primary.200}',
          activeColor: '{primary.100}',
        },
        highlight: {
          background: 'color-mix(in srgb, {primary.300}, transparent 84%)',
          focusBackground: 'color-mix(in srgb, {primary.300}, transparent 76%)',
          color: 'rgba(255,255,255,.87)',
          focusColor: 'rgba(255,255,255,.87)',
        },
        surface: {
          0:   '#ffffff',
          50:  '#e8eff2',
          100: '#d4dee3',
          200: '#aec2cb',
          300: '#7a9baa',
          400: '#5a7f8f',
          500: '#3e5f6e',
          600: '#2a4350',
          700: '#1e3440',
          800: '#162832',
          900: '#101e27',
          950: '#0a141b',
        },
      },
    },
  },
})

const app = createApp(App)

app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Organic,
    options: {
      darkMode: 'class',
      darkModeSelector: '.dark-mode',
    },
  },
})
app.use(ToastService)
app.use(ConfirmationService)
app.directive('tooltip', Tooltip)

// Enable dark mode
//document.documentElement.classList.add('dark-mode')

app.mount('#app')
