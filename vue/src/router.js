// src/router.js
import { createRouter, createWebHistory } from 'vue-router'

import Login from './pages/Login.vue'
import UserPage from './pages/UserPage.vue'
import AdminPage from './pages/AdminPage.vue'
import AccountsPage from './pages/AccountsPage.vue'

import { currentUser } from './store.js'

const routes = [
  { path: '/', component: Login },
  { path: '/user', component: UserPage, meta: { requiresAuth: true } },
  { path: '/admin', component: AdminPage, meta: { requiresAuth: true, role: 'admin' } },
  { path: '/account/:name', component: AccountsPage, meta: { requiresAuth: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  // must be logged in
  if (to.meta.requiresAuth && !currentUser.value) return '/'

  // must have role
  if (to.meta.role && currentUser.value?.role !== to.meta.role) return '/'

  return true
})

export default router