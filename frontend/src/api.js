const JSON_HEADERS = {
  Accept: 'application/json',
}

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }

  const text = await response.text()
  return text ? { detail: text } : null
}

function buildErrorMessage(payload) {
  if (!payload) {
    return 'Unexpected server response.'
  }

  if (typeof payload.detail === 'string') {
    return payload.detail
  }

  const [firstKey] = Object.keys(payload)
  const firstValue = payload[firstKey]
  if (Array.isArray(firstValue) && firstValue.length > 0) {
    return `${firstKey}: ${firstValue[0]}`
  }

  if (typeof firstValue === 'object' && firstValue !== null) {
    const nestedKey = Object.keys(firstValue)[0]
    const nestedValue = firstValue[nestedKey]
    if (Array.isArray(nestedValue) && nestedValue.length > 0) {
      return `${firstKey}.${nestedKey}: ${nestedValue[0]}`
    }
  }

  return 'The request could not be completed.'
}

async function apiRequest(path, { method = 'GET', body, token, isFormData = false } = {}) {
  const headers = { ...JSON_HEADERS }
  if (!isFormData) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) {
    headers.Authorization = `Token ${token}`
  }

  const response = await fetch(path, {
    method,
    headers,
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
  })

  const payload = await parseResponse(response)
  if (!response.ok) {
    throw new Error(buildErrorMessage(payload))
  }

  return payload
}

export function login(credentials) {
  return apiRequest('/api/auth/login/', { method: 'POST', body: credentials })
}

export function fetchCurrentUser(token) {
  return apiRequest('/api/auth/me/', { token })
}

export function logout(token) {
  return apiRequest('/api/auth/logout/', { method: 'POST', token })
}

export function changePassword(token, payload) {
  return apiRequest('/api/auth/change-password/', { method: 'POST', body: payload, token })
}

export function requestPasswordReset(email) {
  return apiRequest('/api/auth/password-reset-request/', {
    method: 'POST',
    body: { email },
  })
}

export function confirmPasswordReset(payload) {
  return apiRequest('/api/auth/password-reset-confirm/', {
    method: 'POST',
    body: payload,
  })
}

export function searchAirports(search) {
  return apiRequest(`/api/airports/?search=${encodeURIComponent(search)}`)
}

export function previewCompensation(payload) {
  return apiRequest('/api/cases/compensation-preview/', {
    method: 'POST',
    body: payload,
  })
}

export function createCase(token, formData) {
  return apiRequest('/api/cases/', {
    method: 'POST',
    body: formData,
    token,
    isFormData: true,
  })
}
