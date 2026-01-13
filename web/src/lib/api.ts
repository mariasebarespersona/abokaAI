/**
 * API Utilities with Authentication
 * 
 * Provides authenticated fetch wrapper for API calls.
 */

import { createClient } from '@/lib/supabase/client'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

/**
 * Get the current auth token from Supabase
 */
export async function getAuthToken(): Promise<string | null> {
  try {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token || null
  } catch {
    return null
  }
}

/**
 * Fetch wrapper that automatically includes auth headers
 */
export async function authFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getAuthToken()
  
  const headers = new Headers(options.headers)
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  
  // Don't set Content-Type for FormData (browser sets it automatically with boundary)
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`
  
  return fetch(url, {
    ...options,
    headers,
  })
}

/**
 * Helper for GET requests
 */
export async function apiGet<T = any>(endpoint: string): Promise<T> {
  const response = await authFetch(endpoint, { method: 'GET' })
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}

/**
 * Helper for POST requests
 */
export async function apiPost<T = any>(endpoint: string, body: any): Promise<T> {
  const response = await authFetch(endpoint, {
    method: 'POST',
    body: body instanceof FormData ? body : JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}

/**
 * Helper for PUT requests
 */
export async function apiPut<T = any>(endpoint: string, body: any): Promise<T> {
  const response = await authFetch(endpoint, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}

/**
 * Helper for DELETE requests
 */
export async function apiDelete<T = any>(endpoint: string): Promise<T> {
  const response = await authFetch(endpoint, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return response.json()
}

