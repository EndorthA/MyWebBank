<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { registerUser } from '../store.js'

const router = useRouter()
const error = ref('')

const form = ref({
  name: '',
  email: '',
  phone: '',
  identificationNumber: '',
  afm: '',
  address: '',
  zipCode: '',
  city: '',
  citizenship: '',
  password: ''
})

async function createAccount() {
  error.value = ''
  const res = await registerUser(form.value)
  if (!res.ok) {
    error.value = res.message
    return
  }
  // after creation, go back to login (or you can go to /user if you prefer)
  router.push('/')
}

function goBack() {
  router.push('/')
}
</script>

<template>
  <div class="page-container">
    <div class="card">
      <h1>Create Account</h1>

      <input v-model="form.name" placeholder="Name" />
      <input v-model="form.email" type="email" placeholder="Email" />
      <input v-model="form.phone" placeholder="Phone" />
      <input v-model="form.identificationNumber" placeholder="Identification Number" />
      <input v-model="form.afm" placeholder="AFM" />
      <input v-model="form.address" placeholder="Address" />
      <input v-model="form.zipCode" placeholder="Zip Code" />
      <input v-model="form.city" placeholder="City" />
      <input v-model="form.citizenship" placeholder="Citizenship" />
      <input v-model="form.password" type="password" placeholder="Password" />

      <button @click="createAccount">
        Create Account
      </button>

      <button class="danger" @click="goBack">
        Back
      </button>

      <p v-if="error" style="color:#d9534f; margin: 8px 0 0;">
        {{ error }}
      </p>
    </div>
  </div>
</template>