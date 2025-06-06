<template>
  <div class="container mx-auto p-4">
    <h1 class="text-3xl font-bold mb-4">Welcome to Fullstack App</h1>
    
    <div class="bg-white shadow-md rounded p-6">
      <h2 class="text-xl font-semibold mb-4">API Test</h2>
      <button 
        @click="fetchMessage" 
        class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
      >
        Test API Connection
      </button>
      
      <div v-if="message" class="mt-4 p-4 bg-gray-100 rounded">
        {{ message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const message = ref('')

const fetchMessage = async () => {
  try {
    const response = await api.get<{ message: string }>('/hello')
    message.value = response.message
  } catch (error) {
    console.error('Failed to fetch message:', error)
    message.value = 'Error connecting to API'
  }
}
</script> 