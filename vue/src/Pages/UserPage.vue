<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { accounts, currentUser, logout } from '../store.js'

const router = useRouter()

const selectedAccount = ref('')
const accountName = ref('')
const currency = ref('EUR')

const myAccounts = computed(() => {
  const email = currentUser.value?.email
  return accounts.value.filter(a => a.ownerEmail === email)
})

const selectedAccountObj = computed(() =>
  myAccounts.value.find(a => a.name === selectedAccount.value) || null
)

function createAccount() {
  if (!accountName.value || !currentUser.value?.email) return

  accounts.value.push({
    name: accountName.value,
    ownerEmail: currentUser.value.email,
    currency: currency.value,
    money: 0,
    status: 'open',
    loans: [],
    transactions: []
  })

  accountName.value = ''
}

function manageAccount() {
  if (selectedAccount.value) router.push(`/account/${selectedAccount.value}`)
}

function exitApp() {
  logout()
  router.push('/')
}
</script>

<template>
  <div class="page-container">
    <div class="card">
      <h1>User Panel</h1>

      <label>Select Account</label>
      <select v-model="selectedAccount">
        <option disabled value="">Choose account</option>
        <option v-for="acc in myAccounts" :key="acc.name" :value="acc.name">
          {{ acc.name }} ({{ acc.currency }}) - Money: {{ acc.money }}
        </option>
      </select>

      <div class="info-box" v-if="selectedAccountObj">
        <strong>Status:</strong>
        <div class="amount">{{ selectedAccountObj.status }}</div>
      </div>

      <button @click="manageAccount" :disabled="!selectedAccount">
        Manage Account
      </button>

      <hr />

      <h3>Create New Account</h3>
      <input v-model="accountName" placeholder="Account Name" />
      <select v-model="currency">
        <option>EUR</option>
        <option>USD</option>
        <option>GBP</option>
      </select>
      <button @click="createAccount">Create Account</button>

      <hr />
      <button class="danger" @click="exitApp">Exit</button>
    </div>
  </div>
</template>

<style scoped>
.info-box {
  border: 1px solid #ddd;
  border-radius: 10px;
  padding: 12px;
  margin: 10px 0;
  background: #fafafa;
}
.amount { margin-top: 6px; font-size: 18px; }
</style>