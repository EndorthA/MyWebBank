// src/store.js
import { ref, watch } from 'vue'
import api from './api.js'

// -------------------- Persistence helpers --------------------
function load(key, fallback) {
  const raw = localStorage.getItem(key)
  return raw ? JSON.parse(raw) : fallback
}

function save(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

// -------------------- Normalizers --------------------
function toNumber(x, fallback = 0) {
  const n = Number(x)
  return Number.isFinite(n) ? n : fallback
}

function normalizeUsers(list) {
  if (!Array.isArray(list)) return []
  return list
    .map((u) => {
      const statusRaw = String(u?.status ?? 'active')
      const status = statusRaw === 'active' || statusRaw === 'frozen' ? statusRaw : 'active'
      return {
        email: String(u?.email ?? '').trim(),
        password: String(u?.password ?? ''),
        role: u?.role === 'admin' ? 'admin' : 'user',
        profile: u?.profile ?? null,
        status, // active | frozen
      }
    })
    .filter((u) => u.email)
}

function normalizeAccounts(list) {
  if (!Array.isArray(list)) return []
  return list
    .map((a) => {
      const statusRaw = String(a?.status ?? 'open')
      const status =
        statusRaw === 'open' || statusRaw === 'frozen' || statusRaw === 'closed'
          ? statusRaw
          : 'open'

      return {
        name: String(a?.name ?? ''),
        accountId: toNumber(a?.accountId ?? a?.account_id, 0),
        customerId: toNumber(a?.customerId ?? a?.customer_id, 0),
        ownerEmail: String(a?.ownerEmail ?? 'user@test.com').trim(), // ✅ NEW
        currency: String(a?.currency ?? 'EUR'),
        money: toNumber(a?.money, 0),
        status, // open | frozen | closed
        loans: Array.isArray(a?.loans)
          ? a.loans.map((l) => ({
              name: String(l?.name ?? ''),
              amount: toNumber(l?.amount, 0),
            }))
          : [],
        transactions: Array.isArray(a?.transactions) // ✅ NEW
          ? a.transactions.map((t) => ({
              id: String(t?.id ?? ''),
              type: String(t?.type ?? ''),
              amount: toNumber(t?.amount, 0),
              note: String(t?.note ?? ''),
              ts: String(t?.ts ?? ''),
            }))
          : [],
      }
    })
    .filter((a) => a.name && a.ownerEmail)
}

// -------------------- Defaults --------------------
const DEFAULT_USERS = [
  { email: 'user@test.com', password: '1234', role: 'user', status: 'active' },
  { email: 'admin@test.com', password: '1234', role: 'admin', status: 'active' },
]

const DEFAULT_ACCOUNTS = [
  { name: 'Main Account', ownerEmail: 'user@test.com', currency: 'EUR', money: 1000, status: 'open', loans: [], transactions: [] },
  { name: 'Savings Account', ownerEmail: 'user@test.com', currency: 'USD', money: 500, status: 'open', loans: [], transactions: [] },
]

// -------------------- Shared state --------------------
export const users = ref(normalizeUsers(load('users', DEFAULT_USERS)))
export const accounts = ref(normalizeAccounts(load('accounts', DEFAULT_ACCOUNTS)))
export const currentUser = ref(load('currentUser', null)) // { email, role } | null

// -------------------- User helpers --------------------
export async function findUserByEmail(email) {
  const e = String(email ?? '').trim()
  if (!e) return { ok: false, message: 'Email is required', user: null }

  try {
    const { data } = await api.get(`/users/email/${encodeURIComponent(e)}`)
    return { ok: true, user: mapManagedUser(data) }
  } catch (error) {
    if (error?.response?.status === 404) {
      return { ok: false, message: 'User not found.', user: null }
    }
    return { ok: false, message: error?.response?.data?.detail || 'Could not fetch user', user: null }
  }
}

// -------------------- Auth --------------------
function mapApiUser(user) {
  return {
    email: String(user?.email ?? '').trim(),
    role: user?.role === 'admin' ? 'admin' : 'user',
  }
}

export async function loginUser(identifier, password) {
  const e = String(identifier ?? '').trim()
  const p = String(password ?? '')
  if (!e || !p) return { ok: false, message: 'Email/username and password required' }

  try {
    const { data } = await api.post('/auth/login', { email: e, password: p })
    localStorage.setItem('access_token', data.access_token)
    currentUser.value = { email: e, role: 'user' }
    await fetchMyAccounts()
    return { ok: true, role: 'user' }
  } catch (error) {
    localStorage.removeItem('access_token')
    return { ok: false, message: error?.response?.data?.detail || 'Invalid user credentials' }
  }
}

export async function loginAdmin(identifier, password) {
  const e = String(identifier ?? '').trim()
  const p = String(password ?? '')
  if (!e || !p) return { ok: false, message: 'Email/username and password required' }

  try {
    const { data } = await api.post('/auth/admin/login', { username: e, password: p })
    localStorage.setItem('access_token', data.access_token)
    currentUser.value = { email: e, role: 'admin' }
    return { ok: true, role: 'admin' }
  } catch (error) {
    localStorage.removeItem('access_token')
    return { ok: false, message: error?.response?.data?.detail || 'Invalid admin credentials' }
  }
}


export function loginAsTest(role) {
  const email = role === 'admin' ? 'admin@test.com' : 'user@test.com'
  const u = users.value.find((x) => x.email === email)
  if (!u) return
  if (u.status === 'frozen') return
  currentUser.value = { email: u.email, role: u.role }
}

export function logout() {
  localStorage.removeItem('access_token')
  currentUser.value = null
}

// -------------------- Account/Profile functions --------------------
export async function createBankAccount(name, currency = 'EUR') {
  const accountName = String(name ?? '').trim()
  const accountCurrency = String(currency ?? 'EUR').trim().toUpperCase()
  const ownerEmail = String(currentUser.value?.email ?? '').trim()

  if (!accountName) return { ok: false, message: 'Account name is required' }
  if (!ownerEmail) return { ok: false, message: 'User not logged in' }

  try {
    const { data: me } = await api.get('/auth/me')
    const customerId = me?.customer_id
    if (!customerId) return { ok: false, message: 'Could not resolve customer' }

    const { data } = await api.post('/accounts/', {
      customer_id: customerId,
      name: accountName,
      currency: accountCurrency,
    })

    const statusRaw = String(data?.status ?? 'active')
    const status = statusRaw === 'closed' || statusRaw === 'frozen' ? statusRaw : 'open'

    accounts.value.push({
      name: accountName,
      ownerEmail,
      currency: String(data?.currency ?? accountCurrency),
      money: toNumber(data?.balance, 0),
      status,
      loans: [],
      transactions: [],
    })
    const refresh = await fetchMyAccounts()
    if (!refresh.ok) return refresh
    return { ok: true }
  } catch (error) {
    return {
      ok: false,
      message: error?.response?.data?.detail || 'Could not create account',
    }
  }
}

export async function fetchMyAccounts() {
  const ownerEmail = String(currentUser.value?.email ?? '').trim()
  if (!ownerEmail) return { ok: false, message: 'User not logged in' }

  try {
    const { data: me } = await api.get('/auth/me')
    const customerId = me?.customer_id
    if (!customerId) return { ok: false, message: 'Could not resolve customer' }

    const { data } = await api.get(`/accounts/customer/${customerId}`)

    const existingTxById = new Map(
      accounts.value
        .filter((a) => a.ownerEmail === ownerEmail)
        .map((a) => [a.accountId, Array.isArray(a.transactions) ? a.transactions : []])
    )

    const mapped = (Array.isArray(data) ? data : []).map((a) => {
      const accountId = toNumber(a?.account_id, 0)
      const statusRaw = String(a?.status ?? 'active')
      const status = statusRaw === 'closed' || statusRaw === 'frozen' ? statusRaw : 'open'

      return {
        name: String(a?.name ?? `Account ${a.account_id}`),
        accountId,
        customerId: toNumber(a?.customer_id, 0),
        ownerEmail,
        currency: String(a?.currency ?? 'EUR'),
        money: toNumber(a?.balance, 0),
        status,
        loans: [],
        transactions: existingTxById.get(accountId) || [],
      }
    })

    accounts.value = [
      ...accounts.value.filter((a) => a.ownerEmail !== ownerEmail),
      ...mapped,
    ]

    return { ok: true }
  } catch (error) {
    return {
      ok: false,
      message: error?.response?.data?.detail || 'Could not load accounts',
    }
  }
}


export async function prepareManageAccount(selectedName) {
  const name = String(selectedName ?? '').trim()
  const ownerEmail = String(currentUser.value?.email ?? '').trim()
  if (!name || !ownerEmail) return { ok: false, message: 'Invalid account selection' }

  const refreshed = await fetchMyAccounts() // API call
  if (!refreshed.ok) return refreshed

  const exists = accounts.value.some(
    (a) => a.ownerEmail === ownerEmail && a.name === name
  )
  if (!exists) return { ok: false, message: 'Account not found' }

  return { ok: true, name }
}

export async function exitSession() {
  try {
    await api.get('/auth/me')
  } catch {
    // ignore
  } finally {
    logout()
  }
  return { ok: true }
}

// Managed account functions
function findMyAccountByName(name) {
  const n = String(name ?? '').trim()
  const ownerEmail = String(currentUser.value?.email ?? '').trim()
  if (!n || !ownerEmail) return null

  return accounts.value.find(
    (a) => a.ownerEmail === ownerEmail && a.name === n
  ) || null
}


export async function updateAccountStatusByName(name, statusValue) {
  const acc = findMyAccountByName(name)
  if (!acc?.accountId) return { ok: false, message: 'Account not found' }

  try {
    await api.put(`/accounts/${acc.accountId}/status`, { status_value: statusValue })
    return await fetchMyAccounts()
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not update account status' }
  }
}

export async function depositByName(name, amount, currency) {
  const acc = findMyAccountByName(name)
  const amt = Number(amount)
  if (!acc?.accountId) return { ok: false, message: 'Account not found' }
  if (!Number.isFinite(amt) || amt <= 0) return { ok: false, message: 'Amount must be positive' }

  try {
    await api.post(`/accounts/${acc.accountId}/deposit`, {
      amount: amt,
      currency: String(currency ?? acc.currency ?? 'EUR').toUpperCase(),
    })
    return await fetchMyAccounts()
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not deposit money' }
  }
}

export async function withdrawByName(name, amount, currency) {
  const acc = findMyAccountByName(name)
  const amt = Number(amount)
  if (!acc?.accountId) return { ok: false, message: 'Account not found' }
  if (!Number.isFinite(amt) || amt <= 0) return { ok: false, message: 'Amount must be positive' }

  try {
    await api.post(`/accounts/${acc.accountId}/withdraw`, {
      amount: amt,
      currency: String(currency ?? acc.currency ?? 'EUR').toUpperCase(),
    })
    return await fetchMyAccounts()
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not withdraw money' }
  }
}

export async function transferByNames(fromName, recipientEmail, recipientAccountName, amount) {
  const from = findMyAccountByName(fromName)
  const toEmail = String(recipientEmail ?? '').trim()
  const toName = String(recipientAccountName ?? '').trim()
  const amt = Number(amount)

  if (!from?.accountId) return { ok: false, message: 'Sender account not found' }
  if (!toEmail || !toName) return { ok: false, message: 'Recipient info is required' }
  if (!Number.isFinite(amt) || amt <= 0) return { ok: false, message: 'Amount must be positive' }

  try {
    const { data: user } = await api.get(`/users/email/${encodeURIComponent(toEmail)}`)
    const { data: recipientAccounts } = await api.get(`/accounts/customer/${user.customer_id}`)

    const target = (Array.isArray(recipientAccounts) ? recipientAccounts : []).find(
      (a) => String(a?.name ?? `Account ${a?.account_id}`) === toName
    )
    if (!target?.account_id) return { ok: false, message: 'Recipient account not found' }

    await api.post('/transactions/', {
      sender_account_id: from.accountId,
      receiver_account_id: target.account_id,
      amount: amt,
      currency: String(from.currency ?? 'EUR').toUpperCase(),
      comment: '',
    })

    return await fetchMyAccounts()
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not complete transfer' }
  }
}

export async function fetchTransferRecipientEmails(options = {}) {
  const myEmail = String(currentUser.value?.email ?? '').trim()
  if (!myEmail) return { ok: false, message: 'User not logged in', items: [] }
  const includeDeleted = options.includeDeleted === true
  const includeSelf = options.includeSelf === true

  try {
    const { data } = await api.get('/users/')
    const items = (Array.isArray(data) ? data : [])
      .filter((u) => includeDeleted || u?.is_deleted !== true)
      .map((u) => String(u?.email ?? '').trim())
      .filter((email) => email && (includeSelf || email !== myEmail))
    return { ok: true, items }
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not load users', items: [] }
  }
}

export async function fetchRecipientAccountNamesByEmail(email) {
  const toEmail = String(email ?? '').trim()
  if (!toEmail) return { ok: false, message: 'Recipient email is required', items: [] }

  try {
    const { data: user } = await api.get(`/users/email/${encodeURIComponent(toEmail)}`)
    const { data: recipientAccounts } = await api.get(`/accounts/customer/${user.customer_id}`)
    const items = (Array.isArray(recipientAccounts) ? recipientAccounts : [])
      .map((a) => String(a?.name ?? `Account ${a?.account_id}`))
      .filter(Boolean)
    return { ok: true, items }
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not load recipient accounts', items: [] }
  }
}

export async function fetchTransactionsByAccountName(name) {
  const acc = findMyAccountByName(name)
  if (!acc?.accountId) return { ok: false, message: 'Account not found', items: [] }

  try {
    const { data } = await api.get(`/transactions/account/${acc.accountId}`)
    const apiItems = (Array.isArray(data) ? data : []).map((t) => ({
      id: String(t?.transaction_id ?? ''),
      type: t?.sender_account_id === acc.accountId ? 'TRANSFER_OUT' : 'TRANSFER_IN',
      amount: toNumber(t?.amount, 0),
      note: String(t?.comment ?? ''),
      ts: String(t?.created_at ?? ''),
    }))

    const localItems = (Array.isArray(acc.transactions) ? acc.transactions : [])
      .filter((t) => t?.type !== 'TRANSFER_OUT' && t?.type !== 'TRANSFER_IN')

    const items = [...apiItems, ...localItems].sort(
      (a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime()
    )

    return { ok: true, items }
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not load transactions', items: [] }
  }
}


// Loan functions
export async function fetchLoansByAccountName(name) {
  const acc = findMyAccountByName(name)
  if (!acc?.customerId) return { ok: false, message: 'Account not found', items: [] }

  try {
    const { data } = await api.get(`/loans/customer/${acc.customerId}`)
    const items = (Array.isArray(data) ? data : []).map((l) => ({
      loanId: Number(l?.loan_id ?? 0),
      name: String(l?.name ?? `Loan ${l?.loan_id}`),
      amount: Number(l?.remaining_debt ?? 0),
      currency: String(l?.currency ?? acc.currency ?? 'EUR'),
    }))
    return { ok: true, items }
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not load loans', items: [] }
  }
}

export async function requestLoanByAccountName(name, loanName, amount) {
  const acc = findMyAccountByName(name)
  const nm = String(loanName ?? '').trim()
  const amt = Number(amount)

  if (!acc?.accountId || !acc?.customerId) return { ok: false, message: 'Account not found' }
  if (!nm) return { ok: false, message: 'Loan name is required' }
  if (!Number.isFinite(amt) || amt <= 0) return { ok: false, message: 'Loan amount must be positive' }

  try {
    await api.post('/loans/', {
      customer_id: acc.customerId,
      name: nm,
      principal: amt,
      remaining_debt: amt,
      currency: String(acc.currency ?? 'EUR').toUpperCase(),
      rate_percentage: 5.5,
    })

    await api.post(`/accounts/${acc.accountId}/deposit`, {
      amount: amt,
      currency: String(acc.currency ?? 'EUR').toUpperCase(),
    })

    await fetchMyAccounts()
    return { ok: true }
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not create loan' }
  }
}

export async function payLoanByAccountName(name, loanId, amount) {
  const acc = findMyAccountByName(name)
  const lid = Number(loanId)
  const amt = Number(amount)

  if (!acc?.accountId) return { ok: false, message: 'Account not found' }
  if (!Number.isFinite(lid) || lid <= 0) return { ok: false, message: 'Loan not found' }
  if (!Number.isFinite(amt) || amt <= 0) return { ok: false, message: 'Payment amount must be positive' }

  try {
    await api.post(`/loans/${lid}/payment`, { amount: amt })

    await api.post(`/accounts/${acc.accountId}/withdraw`, {
      amount: amt,
      currency: String(acc.currency ?? 'EUR').toUpperCase(),
    })

    await fetchMyAccounts()
    return { ok: true }
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not pay loan' }
  }
}

// Admin-create user/admin accounts
export async function createAccountWithRole(email, password, role) {
  const e = String(email ?? '').trim()
  const p = String(password ?? '')
  const r = role === 'admin' ? 'admin' : 'user'

  if (!e || !p) return { ok: false, message: 'Email and password required' }

  try {
    if (r === 'admin') {
      const username = buildAdminUsername(e)
      await api.post('/admins/', {
        username,
        email: e,
        phone: null,
        password: p,
        role: 'admin',
      })
      return { ok: true, username }
    }

    const { afm, identificationNumber } = buildSyntheticIdentity()
    return await registerUser({
      email: e,
      password: p,
      phone: '',
      identificationNumber,
      afm,
      address: '',
      zipCode: '',
      city: '',
      citizenship: '',
      name: '',
    })
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not create account' }
  }
}

// -------------------- Admin functions --------------------
export async function setUserStatus(email, status) {
  if (status !== 'active' && status !== 'frozen') {
    return { ok: false, message: 'Invalid status' }
  }

  const found = await findUserByEmail(email)
  if (!found.ok || !found.user) return found

  try {
    if (status === 'frozen') {
      await api.delete(`/users/${found.user.userId}`)
      return { ok: true, user: { ...found.user, status: 'frozen', isDeleted: true } }
    }

    // Needs backend support (example: PUT /users/{id}/status)
    await api.put(`/users/${found.user.userId}/status`, { status_value: 'active' })
    const refreshed = await findUserByEmail(email)
    return refreshed.ok ? { ok: true, user: refreshed.user } : refreshed
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not update user status' }
  }
}

export async function deleteUser(email) {
  const found = await findUserByEmail(email)
  if (!found.ok || !found.user) return found

  try {
    await api.delete(`/users/${found.user.userId}`)
    accounts.value = accounts.value.filter(a => a.ownerEmail !== found.user.email)
    return { ok: true }
  } catch (error) {
    return { ok: false, message: error?.response?.data?.detail || 'Could not delete user' }
  }
}

export async function registerUser(profile) {
  const email = String(profile?.email ?? '').trim()
  const password = String(profile?.password ?? '')
  const phone = String(profile?.phone ?? '').trim()
  const identificationNumber = String(profile?.identificationNumber ?? '').trim()
  const afm = String(profile?.afm ?? '').trim()
  const address = String(profile?.address ?? '').trim()
  const zipCode = String(profile?.zipCode ?? '').trim()
  const city = String(profile?.city ?? '').trim()
  const citizenship = String(profile?.citizenship ?? '').trim()

  if (!email || !password) return { ok: false, message: 'Email and password required' }
  if (!identificationNumber) return { ok: false, message: 'Identification number is required' }
  if (identificationNumber.length > 10) {
    return { ok: false, message: 'Identification number must be at most 10 characters' }
  }
  if (!afm) return { ok: false, message: 'AFM is required' }
  if (afm.length !== 9) return { ok: false, message: 'AFM must be 9 characters' }

  try {
    await api.get(`/users/email/${encodeURIComponent(email)}`)
    return { ok: false, message: 'Email already exists' }
  } catch (error) {
    if (error?.response?.status && error.response.status !== 404) {
      return {
        ok: false,
        message: error?.response?.data?.detail || 'Could not check existing users',
      }
    }
  }

  let customerId
  try {
    const { data } = await api.post('/customers/', {
      identity_card_num: identificationNumber,
      afm,
      address: address || null,
      zip_code: zipCode || null,
      city: city || null,
      citizenship: citizenship || null,
    })
    customerId = data.customer_id
  } catch (error) {
    return {
      ok: false,
      message: error?.response?.data?.detail || 'Could not create customer',
    }
  }

  try {
    const { data } = await api.post(`/auth/register?customer_id=${customerId}`, {
      customer_id: customerId,
      email,
      phone: phone || null,
      password,
      role: 'customer',
    })

    const mappedUser = mapApiUser(data)
    users.value.push({
      email: mappedUser.email,
      password: '',
      role: mappedUser.role,
      status: 'active',
      profile: {
        name: String(profile?.name ?? ''),
        phone,
        identificationNumber,
        afm,
        address,
        zipCode,
        city,
        citizenship,
      }
    })

    return { ok: true, role: mappedUser.role }
  } catch (error) {
    try {
      // Best-effort rollback if user creation fails after the customer was created.
      await api.delete(`/customers/${customerId}`)
    } catch {
      // Ignore rollback failures and surface the original registration error.
    }

    return {
      ok: false,
      message: error?.response?.data?.detail || 'Could not create user',
    }
  }
}
function mapManagedUser(u) {
  return {
    userId: Number(u?.user_id ?? 0),
    customerId: Number(u?.customer_id ?? 0),
    email: String(u?.email ?? '').trim(),
    role: u?.role === 'customer' ? 'user' : String(u?.role ?? 'user'),
    status: u?.is_deleted ? 'frozen' : 'active',
    isDeleted: Boolean(u?.is_deleted),
  }
}

function buildAdminUsername(email) {
  const local = String(email ?? '').split('@')[0] || 'admin'
  const cleaned = local.toLowerCase().replace(/[^a-z0-9_]/g, '')
  const base = cleaned.length >= 3 ? cleaned : `${cleaned}adm`
  return base.slice(0, 50)
}

function buildSyntheticIdentity() {
  const seed = `${Date.now()}${Math.floor(Math.random() * 1000)}`.replace(/\D/g, '')
  const afm = seed.slice(-9).padStart(9, '0')
  const identificationNumber = (`A${seed}`).slice(0, 10)
  return { afm, identificationNumber }
}

// -------------------- Test reset --------------------
export function resetAll() {
  localStorage.removeItem('accounts')
  localStorage.removeItem('users')
  localStorage.removeItem('currentUser')

  users.value = normalizeUsers(DEFAULT_USERS)
  accounts.value = normalizeAccounts(DEFAULT_ACCOUNTS)
  currentUser.value = null
}

// -------------------- Persistence watchers --------------------
watch(currentUser, (v) => save('currentUser', v), { deep: true })


//watch(users, (v) => save('users', v), { deep: true })
//watch(accounts, (v) => save('accounts', v), { deep: true })
//watch(currentUser, (v) => save('currentUser', v), { deep: true })
//Not needed if db is running^
