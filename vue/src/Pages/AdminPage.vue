<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  exitSession,
  findUserByEmail,
  setUserStatus,
  deleteUser,
  createAccountWithRole,
  fetchTransferRecipientEmails
} from '../store.js'

const router = useRouter()

// -------- Search (panel 1) --------
const searchEmail = ref('')
const searchError = ref('')
const availableUsers = ref([])

const showModal = ref(false)
const selectedUser = ref(null)

async function openUser() {
  searchError.value = ''
  const res = await findUserByEmail(searchEmail.value)

  if (!res.ok || !res.user) {
    searchError.value = res.message || 'User not found.'
    showModal.value = false
    selectedUser.value = null
    return
  }

  selectedUser.value = res.user
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function refreshAvailableUsers() {
  const res = await fetchTransferRecipientEmails({ includeDeleted: true, includeSelf: true })
  if (!res.ok) {
    searchError.value = res.message || 'Could not load users.'
    availableUsers.value = []
    return
  }
  availableUsers.value = res.items
}

async function freezeUser() {
  if (!selectedUser.value) return
  searchError.value = ''
  const res = await setUserStatus(selectedUser.value.email, 'frozen')
  if (!res.ok) {
    searchError.value = res.message
    return
  }
  selectedUser.value = res.user ?? selectedUser.value
}

async function unfreezeUser() {
  if (!selectedUser.value) return
  searchError.value = ''
  const res = await setUserStatus(selectedUser.value.email, 'active')
  if (!res.ok) {
    searchError.value = res.message
    return
  }
  selectedUser.value = res.user ?? selectedUser.value
}

async function removeUser() {
  if (!selectedUser.value) return
  searchError.value = ''
  const res = await deleteUser(selectedUser.value.email)
  if (!res.ok) {
    searchError.value = res.message
    return
  }
  closeModal()
  await refreshAvailableUsers()
}

// -------- Create account (panel 2) --------
const newEmail = ref('')
const newPassword = ref('')
const newRole = ref('user')
const createError = ref('')
const createSuccess = ref('')

async function createAccount() {
  createError.value = ''
  createSuccess.value = ''

  const createdEmail = String(newEmail.value).trim()
  const createdRole = newRole.value
  const res = await createAccountWithRole(newEmail.value, newPassword.value, newRole.value)
  if (!res.ok) {
    createError.value = res.message
    return
  }

  if (createdRole === 'admin' && res.username) {
    createSuccess.value = `Created admin account: ${createdEmail} (username: ${res.username})`
  } else {
    createSuccess.value = `Created ${createdRole} account: ${createdEmail}`
  }
  newEmail.value = ''
  newPassword.value = ''
  newRole.value = 'user'
  await refreshAvailableUsers()
}

async function exitAdmin() {
  await exitSession()
  router.push('/')
}

onMounted(async () => {
  await refreshAvailableUsers()
})
</script>

<template>
  <div class="page-container">
    <!-- Left card: Search / Manage -->
    <div class="card" style="margin-right: 16px;">
      <h1>Admin Panel</h1>

      <label>Search user by email</label>
      <select v-model="searchEmail">
        <option disabled value="">Choose email</option>
        <option v-for="e in availableUsers" :key="e" :value="e">{{ e }}</option>
      </select>

      <button @click="openUser">
        Modify
      </button>

      <button @click="refreshAvailableUsers">
        Refresh Users
      </button>

      <p v-if="searchError" style="color:#d9534f; margin: 8px 0 0;">
        {{ searchError }}
      </p>

      <hr />

      <button class="danger" @click="exitAdmin">
        Exit
      </button>
    </div>

    <!-- Right card: Create accounts -->
    <div class="card">
      <h1>Create Account</h1>

      <label>Email</label>
      <input v-model="newEmail" type="email" placeholder="new@example.com" />

      <label>Password</label>
      <input v-model="newPassword" type="password" placeholder="password" />

      <label>Role</label>
      <select v-model="newRole">
        <option value="user">user</option>
        <option value="admin">admin</option>
      </select>

      <button @click="createAccount">
        Create
      </button>

      <p v-if="createError" style="color:#d9534f; margin: 8px 0 0;">
        {{ createError }}
      </p>

      <p v-if="createSuccess" style="color: #2e7d32; margin: 8px 0 0;">
        {{ createSuccess }}
      </p>
    </div>

    <!-- Modal (search results) -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-card">
        <h2 style="margin-top:0;">User Info</h2>

        <p><strong>Email:</strong> {{ selectedUser?.email }}</p>
        <p><strong>Status:</strong> {{ selectedUser?.status }}</p>
        <p><strong>Role:</strong> {{ selectedUser?.role }}</p>

        <hr />

        <button @click="freezeUser" :disabled="selectedUser?.status === 'frozen'">
          Freeze
        </button>

        <button @click="unfreezeUser" :disabled="selectedUser?.status === 'active'">
          Unfreeze
        </button>

        <button class="danger" @click="removeUser">
          Delete User
        </button>

        <hr />

        <button @click="closeModal">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* modal styles only */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px;
}

.modal-card {
  background: white;
  width: 420px;
  border-radius: 10px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.2);
  padding: 24px;
}

</style>
