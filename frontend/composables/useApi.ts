export const useApi = () => {
  const config = useRuntimeConfig()
  const baseUrl = 'http://localhost:8000/api'

  const fetchApi = async <T>(endpoint: string, options: RequestInit = {}): Promise<T> => {
    try {
      const response = await fetch(`${baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('API call failed:', error)
      throw error
    }
  }

  return {
    get: <T>(endpoint: string) => fetchApi<T>(endpoint),
    post: <T>(endpoint: string, data: any) => 
      fetchApi<T>(endpoint, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    put: <T>(endpoint: string, data: any) =>
      fetchApi<T>(endpoint, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: <T>(endpoint: string) =>
      fetchApi<T>(endpoint, {
        method: 'DELETE',
      }),
  }
} 