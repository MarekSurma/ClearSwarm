import { createRouter, createWebHistory } from 'vue-router'
import RunnerPage from '@/pages/RunnerPage.vue'
import VisualEditorPage from '@/pages/VisualEditorPage.vue'
import ActionPlanPage from '@/pages/ActionPlanPage.vue'
import ProjectFilesPage from '@/pages/ProjectFilesPage.vue'

const routes = [
  {
    path: '/',
    name: 'runner',
    component: RunnerPage,
    meta: { title: 'Agent Runner' },
  },
  {
    path: '/visual-editor',
    name: 'visual-editor',
    component: VisualEditorPage,
    meta: { title: 'Visual Editor' },
  },
  {
    path: '/action-plans',
    name: 'action-plans',
    component: ActionPlanPage,
    meta: { title: 'Action Plans' },
  },
  {
    path: '/project-files',
    name: 'project-files',
    component: ProjectFilesPage,
    meta: { title: 'Project Files' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = `ClearSwarm - ${title || 'Web Interface'}`
})

export default router
