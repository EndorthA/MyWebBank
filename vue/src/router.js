// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
// Renamed to Pages instead of pages because typescript is being stupid
import Login from './Pages/Login.vue'
import UserPage from './Pages/UserPage.vue'
import AdminPage from './Pages/AdminPage.vue'
import AccountsPage from './Pages/AccountsPage.vue'
import Register from './Pages/Register.vue'

import { currentUser } from './store.js'

const routes = [
  { path: '/', component: Login },
  { path: '/user', component: UserPage, meta: { requiresAuth: true } },
  { path: '/admin', component: AdminPage, meta: { requiresAuth: true, role: 'admin' } },
  { path: '/account/:name', component: AccountsPage, meta: { requiresAuth: true } },
  { path: '/register', component: Register }
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