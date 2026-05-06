import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import CrawlerView from '../views/CrawlerView.vue'
import QuestionsView from '../views/QuestionsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/crawler',
      name: 'crawler',
      component: CrawlerView
    },
    {
      path: '/questions',
      name: 'questions',
      component: QuestionsView
    }
  ]
})

export default router
