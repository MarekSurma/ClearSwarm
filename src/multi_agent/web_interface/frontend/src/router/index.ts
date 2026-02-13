import { createRouter, createWebHistory } from 'vue-router'
import RunnerPage from '@/pages/RunnerPage.vue'
import EditorPage from '@/pages/EditorPage.vue'
import VisualEditorPage from '@/pages/VisualEditorPage.vue'

const routes = [
  {
    path: '/',
    name: 'runner',
    component: RunnerPage,
    meta: { title: 'Agent Runner' },
  },
  {
    path: '/editor',
    name: 'editor',
    component: EditorPage,
    meta: { title: 'Agent Editor' },
  },
  {
    path: '/visual-editor',
    name: 'visual-editor',
    component: VisualEditorPage,
    meta: { title: 'Visual Editor' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = `ClearSwarm - ${title || 'Web Interface'}`
})

export default router
