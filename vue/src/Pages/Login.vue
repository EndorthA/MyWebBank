<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, loginAsTest, resetAll } from '../store.js'

const router = useRouter()

const email = ref('')
const password = ref('')
const error = ref('')

async function doLogin() {
  error.value = ''
  const res = await login(email.value.trim(), password.value)
  if (!res.ok) {
    error.value = res.message
    return
  }
  router.push(res.role === 'admin' ? '/admin' : '/user')
}


function testUser() {
  loginAsTest('user')
  router.push('/user')
}

function testAdmin() {
  loginAsTest('admin')
  router.push('/admin')
}

function goRegister() {
  router.push('/register')
}

function doReset() {
  resetAll()
  email.value = ''
  password.value = ''
  error.value = ''
}
</script>

<template>
  <div class="page-container">
    <div class="card">
      <h1>Login</h1>

      <input v-model="email" type="text" placeholder="Email or Username" />
      <input v-model="password" type="password" placeholder="Password" />

      <button @click="doLogin">Login</button>

      <!-- NEW: replace previous method -->
      <button @click="goRegister">Create Account</button>

      <p v-if="error" style="color:#d9534f; margin: 8px 0 0;">
        {{ error }}
      </p>

      <hr />

      <button @click="testUser">Test User (pre-created)</button>
      <button @click="testAdmin">Test Admin (pre-created)</button>

      <button class="danger" @click="doReset">
        TEST: Reset Everything
      </button>
    </div>
  </div>
</template>
