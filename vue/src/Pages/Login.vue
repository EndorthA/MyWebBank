<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, createUser, loginAsTest, resetAll } from '../store.js'

const router = useRouter()

const email = ref('')
const password = ref('')
const error = ref('')

function doLogin() {
  error.value = ''
  const res = login(email.value.trim(), password.value)
  if (!res.ok) {
    error.value = res.message
    return
  }
  router.push(res.role === 'admin' ? '/admin' : '/user')
}

function doCreateAccount() {
  error.value = ''
  const res = createUser(email.value.trim(), password.value)
  if (!res.ok) {
    error.value = res.message
    return
  }
  router.push('/user')
}

function testUser() {
  loginAsTest('user')
  router.push('/user')
}

function testAdmin() {
  loginAsTest('admin')
  router.push('/admin')
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

      <input v-model="email" type="email" placeholder="Email" />
      <input v-model="password" type="password" placeholder="Password" />

      <button @click="doLogin">Login</button>
      <button @click="doCreateAccount">Create Account</button>

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