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
      50:  '#f0f7fa',
      100: '#d9edf4',
      200: '#b3dbe9',
      300: '#82c4d9',
      400: '#5aadc9',
      500: '#3d94b5',
      600: '#2f7a9a',
      700: '#26617b',
      800: '#1f4f65',
      900: '#1a3f52',
      950: '#112d3b',
    },
    colorScheme: {
      light: {
        primary: {
          color: '{primary.500}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.600}',
          activeColor: '{primary.700}',
        },
        highlight: {
          background: '{primary.50}',
          focusBackground: '{primary.100}',
          color: '{primary.700}',
          focusColor: '{primary.800}',
        },
        surface: {
          0:   '#ffffff',
          50:  '#f7fafb',
          100: '#eff5f7',
          200: '#e2ecf0',
          300: '#d0dee4',
          400: '#a8bfc9',
          500: '#7a9baa',
          600: '#5a7f8f',
          700: '#3e5f6e',
          800: '#2a4350',
          900: '#1c3340',
          950: '#0f2029',
        },
      },
      dark: {
        primary: {
          color: '{primary.400}',
          contrastColor: '{surface.900}',
          hoverColor: '{primary.300}',
          activeColor: '{primary.200}',
        },
        highlight: {
          background: 'color-mix(in srgb, {primary.400}, transparent 84%)',
          focusBackground: 'color-mix(in srgb, {primary.400}, transparent 76%)',
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
