<template>
  <div class="container mx-auto p-4">
    <h1 class="text-3xl font-bold mb-8">PDF Auto-Extraction System</h1>
    
    <!-- File Upload Section -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 class="text-xl font-semibold mb-4">Upload Documents</h2>
      <div class="space-y-4">
        <div class="flex items-center space-x-4">
          <input
            type="file"
            @change="handleFileUpload"
            multiple
            accept=".pdf"
            class="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100"
          />
          <input
            v-model="partNumber"
            type="text"
            placeholder="Part Number (optional)"
            class="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          @click="processDocuments"
          :disabled="!selectedFiles.length"
          class="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          Process Documents
        </button>
      </div>
    </div>

    <!-- Results Section -->
    <div v-if="extractionResults.length" class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 class="text-xl font-semibold mb-4">Extracted Information</h2>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Attribute</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Extracted Value</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ground Truth</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="result in extractionResults" :key="result.attribute">
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ result.attribute }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ result.value }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <span :class="{
                  'px-2 py-1 rounded-full text-xs font-semibold': true,
                  'bg-green-100 text-green-800': result.source === 'web',
                  'bg-blue-100 text-blue-800': result.source === 'pdf',
                  'bg-gray-100 text-gray-800': result.source === 'none'
                }">
                  {{ result.source }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <input
                  v-model="result.ground_truth"
                  type="text"
                  class="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter ground truth"
                />
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <span :class="{
                  'px-2 py-1 rounded-full text-xs font-semibold': true,
                  'bg-green-100 text-green-800': result.is_success,
                  'bg-red-100 text-red-800': result.is_error,
                  'bg-yellow-100 text-yellow-800': result.is_not_found,
                  'bg-orange-100 text-orange-800': result.is_rate_limit
                }">
                  {{ getStatusText(result) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Metrics Section -->
    <div v-if="metrics" class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 class="text-xl font-semibold mb-4">Metrics</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="text-sm font-medium text-gray-500">Total Fields</h3>
          <p class="mt-1 text-2xl font-semibold text-gray-900">{{ metrics.total_fields }}</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="text-sm font-medium text-gray-500">Success Rate</h3>
          <p class="mt-1 text-2xl font-semibold text-gray-900">{{ (metrics.success_rate * 100).toFixed(1) }}%</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="text-sm font-medium text-gray-500">Error Rate</h3>
          <p class="mt-1 text-2xl font-semibold text-gray-900">{{ (metrics.error_rate * 100).toFixed(1) }}%</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="text-sm font-medium text-gray-500">Not Found Rate</h3>
          <p class="mt-1 text-2xl font-semibold text-gray-900">{{ (metrics.not_found_rate * 100).toFixed(1) }}%</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="text-sm font-medium text-gray-500">Rate Limit Rate</h3>
          <p class="mt-1 text-2xl font-semibold text-gray-900">{{ (metrics.rate_limit_rate * 100).toFixed(1) }}%</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="text-sm font-medium text-gray-500">Exact Match Accuracy</h3>
          <p class="mt-1 text-2xl font-semibold text-gray-900">{{ (metrics.exact_match_accuracy * 100).toFixed(1) }}%</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="text-sm font-medium text-gray-500">Case Insensitive Accuracy</h3>
          <p class="mt-1 text-2xl font-semibold text-gray-900">{{ (metrics.case_insensitive_accuracy * 100).toFixed(1) }}%</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <h3 class="text-sm font-medium text-gray-500">Avg Latency</h3>
          <p class="mt-1 text-2xl font-semibold text-gray-900">{{ metrics.avg_latency.toFixed(2) }}s</p>
        </div>
      </div>
    </div>

    <!-- Export Section -->
    <div v-if="extractionResults.length" class="bg-white rounded-lg shadow-md p-6">
      <h2 class="text-xl font-semibold mb-4">Export Results</h2>
      <div class="flex space-x-4">
        <button
          @click="exportResults"
          class="bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700"
        >
          Export Results (CSV)
        </button>
        <button
          @click="exportMetrics"
          class="bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700"
        >
          Export Metrics (JSON)
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRuntimeConfig } from 'nuxt/app'

const selectedFiles = ref([])
const partNumber = ref('')
const extractionResults = ref([])
const metrics = ref(null)

const handleFileUpload = (event) => {
  selectedFiles.value = Array.from(event.target.files)
}

const getStatusText = (result) => {
  if (result.is_success) return 'Success'
  if (result.is_error) return 'Error'
  if (result.is_not_found) return 'Not Found'
  if (result.is_rate_limit) return 'Rate Limited'
  return 'Unknown'
}

const processDocuments = async () => {
  try {
    // Create FormData
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('files', file)
    })
    if (partNumber.value) {
      formData.append('part_number', partNumber.value)
    }

    // Get API base URL from runtime config
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase

    // Process documents
    const response = await fetch(`${apiBase}/extract/process`, {
      method: 'POST',
      body: formData,
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      },
      mode: 'cors'
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      throw new Error(errorData?.detail || `Failed to process documents: ${response.status} ${response.statusText}`)
    }

    const results = await response.json()
    extractionResults.value = results

    // Calculate metrics
    const metricsResponse = await fetch(`${apiBase}/extract/metrics`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      credentials: 'include',
      mode: 'cors',
      body: JSON.stringify({ results })
    })

    if (!metricsResponse.ok) {
      const errorData = await metricsResponse.json().catch(() => null)
      throw new Error(errorData?.detail || 'Failed to calculate metrics')
    }

    metrics.value = await metricsResponse.json()

  } catch (error) {
    console.error('Error:', error)
    alert(error.message || 'An error occurred while processing the documents')
  }
}

const exportResults = () => {
  // Convert results to CSV
  const headers = ['Attribute', 'Value', 'Source', 'Ground Truth', 'Status']
  const csvContent = [
    headers.join(','),
    ...extractionResults.value.map(result => [
      result.attribute,
      result.value,
      result.source,
      result.ground_truth || '',
      getStatusText(result)
    ].join(','))
  ].join('\n')

  // Create and download file
  const blob = new Blob([csvContent], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'extraction_results.csv'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

const exportMetrics = () => {
  // Convert metrics to JSON
  const jsonContent = JSON.stringify(metrics.value, null, 2)

  // Create and download file
  const blob = new Blob([jsonContent], { type: 'application/json' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'extraction_metrics.json'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}
</script>

<style scoped>
.container {
  max-width: 1200px;
}
</style> 