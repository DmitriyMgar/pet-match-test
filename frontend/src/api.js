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

export function fetchStats() {
  return request('/stats')
}

export function fetchEvaluations(limit = 20, offset = 0) {
  return request(`/evaluations?limit=${limit}&offset=${offset}`)
}

export function fetchRules() {
  return request('/rules')
}

export function reloadRules() {
  return request('/rules/reload', { method: 'POST' })
}

export function validateRules() {
  return request('/rules/validate', { method: 'POST' })
}

export async function fetchRulesRaw() {
  const response = await fetch(`${API_BASE}/rules/raw`)
  if (!response.ok) throw new Error(response.statusText)
  return response.text()
}

export function saveRules(yamlContent) {
  return request('/rules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ yaml_content: yamlContent }),
  })
}
