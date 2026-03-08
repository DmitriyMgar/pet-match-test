const API_BASE = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options)
  if (!response.ok) {
    let message
    try {
      const body = await response.json()
      message = body.detail || body.message || response.statusText
    } catch {
      message = response.statusText
    }
    throw new Error(message)
  }
  return response.json()
}

export function fetchPetTypes() {
  return request('/pet-types')
}

export function evaluate(petType, profile) {
  return request('/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pet_type: petType, profile }),
  })
}
