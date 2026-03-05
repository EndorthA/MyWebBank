<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { accounts, users, currentUser, fetchMyAccounts, updateAccountStatusByName, depositByName, withdrawByName, transferByNames, fetchTransactionsByAccountName } from '../store.js'

const route = useRoute()
const router = useRouter()
const accountName = route.params.name

const account = computed(() => {
  const a = accounts.value.find(acc => acc.name === accountName) || null
  // optional safety: only owner can view
  if (a && currentUser.value?.role !== 'admin' && a.ownerEmail !== currentUser.value?.email) return null
  return a
})

const isLocked = computed(() => {
  const s = account.value?.status
  return s === 'frozen' || s === 'closed'
})

const error = ref('')

// ---------- Transaction ID + logging ----------
const showLog = ref(false)
const transactionLog = ref([])

async function refreshTransactionLog() {
  const res = await fetchTransactionsByAccountName(accountName)
  if (!res.ok) {
    error.value = res.message
    return
  }
  transactionLog.value = res.items
}

async function toggleLog() {
  showLog.value = !showLog.value
  if (showLog.value) await refreshTransactionLog()
}

function emailNumber(ownerEmail) {
  const idx = users.value.findIndex(u => u.email === ownerEmail)
  return idx === -1 ? 0 : idx + 1
}

function accountNumber(ownerEmail, accName) {
  const list = accounts.value.filter(a => a.ownerEmail === ownerEmail)
  const idx = list.findIndex(a => a.name === accName)
  return idx === -1 ? 0 : idx + 1
}

function nextTransactionNumber(acc) {
  const n = Array.isArray(acc.transactions) ? acc.transactions.length : 0
  return n + 1
}

function addTransaction(type, amount, note = '') {
  if (!account.value) return
  const acc = account.value

  if (!Array.isArray(acc.transactions)) acc.transactions = []

  const X = emailNumber(acc.ownerEmail)
  const Y = accountNumber(acc.ownerEmail, acc.name)
  const Z = nextTransactionNumber(acc)

  const id = `${X}.${Y}.${Z}`

  acc.transactions.push({
    id,
    type,
    amount: Number(amount),
    note,
    ts: new Date().toISOString()
  })
}


// ---------- Close / Reopen ----------
async function closeAccount() {
  if (!account.value) return
  error.value = ''

  const res = await updateAccountStatusByName(accountName, 'closed')
  if (!res.ok) {
    error.value = res.message
    return
  }
}

async function reopenAccount() {
  if (!account.value) return
  error.value = ''

  const res = await updateAccountStatusByName(accountName, 'active')
  if (!res.ok) {
    error.value = res.message
    return
  }
}

// ---------- Add Money ----------
const addMoneyAmount = ref('')
async function addMoney() {
  error.value = ''
  if (!account.value || isLocked.value) return

  const amt = Number(addMoneyAmount.value)
  if (!Number.isFinite(amt) || amt <= 0) {
    error.value = 'Add money amount must be positive.'
    return
  }

  const res = await depositByName(accountName, amt, account.value.currency)
  if (!res.ok) {
    error.value = res.message
    return
  }

  addMoneyAmount.value = ''
  if (showLog.value) await refreshTransactionLog()
}

// ---------- Withdraw ----------
const withdrawAmount = ref('')
async function withdrawMoney() {
  error.value = ''
  if (!account.value || isLocked.value) return

  const amt = Number(withdrawAmount.value)
  if (!Number.isFinite(amt) || amt <= 0) {
    error.value = 'Withdrawal amount must be positive.'
    return
  }

  const res = await withdrawByName(accountName, amt, account.value.currency)
  if (!res.ok) {
    error.value = res.message
    return
  }

  withdrawAmount.value = ''
  if (showLog.value) await refreshTransactionLog()
}

// ---------- Loans ----------
const loanName = ref('')
const loanAmount = ref('')
const selectedLoanName = ref('')

const selectedLoan = computed(() => {
  if (!account.value) return null
  return account.value.loans.find(l => l.name === selectedLoanName.value) || null
})

const loanRemaining = computed(() => selectedLoan.value ? selectedLoan.value.amount : '')

function requestLoan() {
  error.value = ''
  if (!account.value || isLocked.value) return
  const amt = Number(loanAmount.value)
  if (!loanName.value.trim()) { error.value = 'Loan name is required.'; return }
  if (!Number.isFinite(amt) || amt <= 0) { error.value = 'Loan amount must be positive.'; return }

  account.value.loans.push({ name: loanName.value.trim(), amount: amt })
  account.value.money += amt

  selectedLoanName.value = loanName.value.trim()
  loanName.value = ''
  loanAmount.value = ''

  addTransaction('LOAN_CREATED', amt, `Loan: ${selectedLoanName.value}`)
}

function payLoan() {
  error.value = ''
  if (!account.value || !selectedLoan.value || isLocked.value) return
  const remaining = Number(selectedLoan.value.amount)
  if (!Number.isFinite(remaining) || remaining <= 0) return
  if (account.value.money < remaining) { error.value = 'Not enough money to pay this loan.'; return }

  account.value.money -= remaining
  selectedLoan.value.amount = 0

  addTransaction('LOAN_PAID', remaining, `Loan: ${selectedLoanName.value}`)
}

// ---------- Transfer ----------
const transferAmount = ref('')
const recipientEmail = ref('')
const recipientAccountName = ref('')

const recipientEmails = computed(() => users.value.map(u => u.email))

watch(recipientEmail, () => { recipientAccountName.value = '' })

// Only show accounts owned by selected recipient email
const recipientAccountNames = computed(() => {
  if (!recipientEmail.value) return []
  return accounts.value
    .filter(a => a.ownerEmail === recipientEmail.value)
    .map(a => a.name)
})

async function doTransfer() {
  error.value = ''
  if (!account.value || isLocked.value) return

  const amt = Number(transferAmount.value)
  if (!Number.isFinite(amt) || amt <= 0) { error.value = 'Transfer amount must be positive.'; return }
  if (!recipientEmail.value) { error.value = 'Choose a recipient email.'; return }
  if (!recipientAccountName.value) { error.value = 'Choose a recipient account.'; return }

  const res = await transferByNames(
    accountName,
    recipientEmail.value,
    recipientAccountName.value,
    amt
  )
  if (!res.ok) {
    error.value = res.message
    return
  }

  transferAmount.value = ''
  recipientEmail.value = ''
  recipientAccountName.value = ''
  if (showLog.value) await refreshTransactionLog()
}

// ---------- Navigation ----------
function goBack() { router.push('/user') }

function deleteAccount() {
  const idx = accounts.value.findIndex(a => a.name === accountName)
  if (idx !== -1) accounts.value.splice(idx, 1)
  router.push('/user')
}

onMounted(async () => {
  await fetchMyAccounts()
})

</script>

<template>
  <div class="page-container" v-if="account">
    <div class="card">
      <h1>Account: {{ account.name }}</h1>
      <p>Owner: {{ account.ownerEmail }}</p>
      <p>Currency: {{ account.currency }}</p>

      <div class="info-box">
        <strong>Status:</strong>
        <div class="amount">{{ account.status }}</div>
      </div>

      <div class="info-box">
        <strong>Money available:</strong>
        <div class="amount">{{ account.money }}</div>
      </div>

      <p v-if="error" style="color:#d9534f;">{{ error }}</p>

      <button v-if="account.status !== 'closed'" class="danger" @click="closeAccount">
        CLOSE ACCOUNT
      </button>

      <button v-if="account.status === 'closed'" @click="reopenAccount">
        Re-Open Account
      </button>

      <hr />

      <h3>Add Money</h3>
      <input v-model="addMoneyAmount" :disabled="isLocked" placeholder="Amount" />
      <button @click="addMoney" :disabled="isLocked">Add Money</button>

      <hr />

      <h3>Withdraw Money</h3>
      <input v-model="withdrawAmount" :disabled="isLocked" placeholder="Amount to withdraw" />
      <button @click="withdrawMoney" :disabled="isLocked">Withdraw</button>

      <hr />

      <h3>Transfer</h3>
      <input v-model="transferAmount" :disabled="isLocked" placeholder="Amount" />

      <label>To user (email)</label>
      <select v-model="recipientEmail" :disabled="isLocked">
        <option disabled value="">Choose email</option>
        <option v-for="e in recipientEmails" :key="e" :value="e">{{ e }}</option>
      </select>

      <label>To account (account name)</label>
      <select v-model="recipientAccountName" :disabled="isLocked || !recipientEmail">
        <option disabled value="">Choose account</option>
        <option v-for="n in recipientAccountNames" :key="n" :value="n">{{ n }}</option>
      </select>

      <button @click="doTransfer" :disabled="isLocked">Transfer</button>

      <hr />

      <h3>Request Loan</h3>
      <input v-model="loanName" :disabled="isLocked" placeholder="Loan Name" />
      <input v-model="loanAmount" :disabled="isLocked" placeholder="Loan Amount" />
      <button @click="requestLoan" :disabled="isLocked">Request Loan</button>

      <hr />

      <label>Loans</label>
      <select v-model="selectedLoanName" :disabled="isLocked">
        <option disabled value="">Choose a loan</option>
        <option v-for="loan in account.loans" :key="loan.name" :value="loan.name">{{ loan.name }}</option>
      </select>

      <div class="info-box" v-if="selectedLoan">
        <strong>Loan amount remaining:</strong>
        <div class="amount">{{ loanRemaining }}</div>
      </div>

      <button @click="payLoan" :disabled="isLocked || !selectedLoan">Pay Loan</button>

      <hr />

      <!-- Transaction Log -->
      <button @click="toggleLog">
        {{ showLog ? 'Hide Transaction Log' : 'Generate Transaction Log' }}
      </button>

      <div v-if="showLog" class="log-box">
        <div v-if="!transactionLog.length">No transactions yet.</div>
        <div v-for="t in transactionLog" :key="t.id" class="log-row">
          <div><strong>{{ t.id }}</strong> — {{ t.type }} — {{ t.amount }}</div>
          <div class="small">{{ t.note }}</div>
          <div class="small">{{ t.ts }}</div>
        </div>
      </div>

      <hr />

      <button @click="goBack">Return</button>
      <button class="danger" @click="deleteAccount">Delete Account</button>
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

button:disabled,
input:disabled,
select:disabled {
  background-color: #cccccc !important;
  color: #666 !important;
  cursor: not-allowed;
  opacity: 0.6;
}

.log-box {
  border: 1px solid #ddd;
  border-radius: 10px;
  padding: 12px;
  margin-top: 10px;
  background: #fafafa;
  max-height: 220px;
  overflow: auto;
}
.log-row {
  padding: 8px 0;
  border-bottom: 1px solid #e6e6e6;
}
.log-row:last-child { border-bottom: none; }
.small { font-size: 12px; color: #555; }
</style>