import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import CrawlerView from '../views/CrawlerView.vue'
import SettingsView from '../views/SettingsView.vue'
import FavoritesView from '../views/FavoritesView.vue'
import PromptsView from '../views/PromptsView.vue'
import ReviewView from '../views/ReviewView.vue'

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
      path: '/favorites',
      name: 'favorites',
      component: FavoritesView
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView
    },
    {
      path: '/prompts',
      name: 'prompts',
      component: PromptsView
    },
    {
      path: '/review',
      name: 'review',
      component: ReviewView
    }
  ]
})

export default router
