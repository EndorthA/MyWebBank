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
export function findUserByEmail(email) {
  const e = String(email ?? '').trim()
  return users.value.find((u) => u.email === e) || null
}

// -------------------- Auth --------------------
function mapApiUser(user) {
  return {
    email: String(user?.email ?? '').trim(),
    role: user?.role === 'admin' ? 'admin' : 'user',
  }
}

export async function login(email, password) {
  const e = String(email ?? '').trim()
  const p = String(password ?? '')

  if (!e || !p) return { ok: false, message: 'Email and password required' }

  try {
    const { data } = await api.post('/auth/login', { email: e, password: p })
    localStorage.setItem('access_token', data.access_token)
    currentUser.value = { email: e, role: 'user' }
    await fetchMyAccounts()
    return { ok: true, role: 'user' }
  } catch (error) {
    localStorage.removeItem('access_token')
    return {
      ok: false,
      message: error?.response?.data?.detail || 'Invalid email or password',
    }
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
    const mapped = (Array.isArray(data) ? data : []).map((a) => {
      const statusRaw = String(a?.status ?? 'active')
      const status = statusRaw === 'closed' || statusRaw === 'frozen' ? statusRaw : 'open'
      return {
        name: String(a?.name ?? `Account ${a.account_id}`),
        ownerEmail,
        currency: String(a?.currency ?? 'EUR'),
        money: toNumber(a?.balance, 0),
        status,
        loans: [],
        transactions: [],
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


// Admin-create user/admin accounts
export function createAccountWithRole(email, password, role) {
  const e = String(email ?? '').trim()
  const p = String(password ?? '')

  if (!e || !p) return { ok: false, message: 'Email and password required' }
  if (users.value.some((u) => u.email === e)) return { ok: false, message: 'Email already exists' }

  const r = role === 'admin' ? 'admin' : 'user'
  users.value.push({ email: e, password: p, role: r, status: 'active' })
  return { ok: true }
}

// -------------------- Admin functions --------------------
export function setUserStatus(email, status) {
  const u = findUserByEmail(email)
  if (!u) return { ok: false, message: 'User not found' }
  if (status !== 'active' && status !== 'frozen') return { ok: false, message: 'Invalid status' }

  u.status = status
  if (currentUser.value?.email === u.email && status === 'frozen') currentUser.value = null
  return { ok: true }
}

export function deleteUser(email) {
  const e = String(email ?? '').trim()
  const idx = users.value.findIndex((u) => u.email === e)
  if (idx === -1) return { ok: false, message: 'User not found' }

  // delete their bank accounts too
  accounts.value = accounts.value.filter(a => a.ownerEmail !== e)

  if (currentUser.value?.email === e) currentUser.value = null
  users.value.splice(idx, 1)
  return { ok: true }
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
watch(users, (v) => save('users', v), { deep: true })
watch(accounts, (v) => save('accounts', v), { deep: true })
watch(currentUser, (v) => save('currentUser', v), { deep: true })
