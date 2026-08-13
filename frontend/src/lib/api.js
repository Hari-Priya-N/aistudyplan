const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

function getToken() {
  return localStorage.getItem('pathwise_token')
}

export function setToken(token) {
  if (token) localStorage.setItem('pathwise_token', token)
  else localStorage.removeItem('pathwise_token')
}

async function request(path, { method = 'GET', body, isForm = false, auth = true } = {}) {
  const headers = {}
  if (!isForm) headers['Content-Type'] = 'application/json'
  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  })

  let data = null
  const text = await res.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!res.ok) {
    const detail = data && data.detail ? data.detail : `Request failed (${res.status})`
    throw new ApiError(typeof detail === 'string' ? detail : JSON.stringify(detail), res.status, detail)
  }
  return data
}

export const api = {
  base: API_BASE,
  signup: (payload) => request('/auth/signup', { method: 'POST', body: payload, auth: false }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload, auth: false }),
  me: () => request('/auth/me'),

  uploadSyllabus: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/syllabus/upload', { method: 'POST', body: form, isForm: true })
  },
  syllabusStatus: (documentId) => request(`/syllabus/${documentId}/status`),
  listSyllabi: () => request('/syllabus/'),
  deleteSyllabus: (documentId) => request(`/syllabus/${documentId}`, { method: 'DELETE' }),

  generateStudyPlan: (documentId) =>
    request('/study-plan/generate', { method: 'POST', body: { document_id: documentId } }),
  getStudyPlan: () => request('/study-plan/'),

  listTopics: (documentId) =>
    request(`/topics/${documentId ? `?document_id=${documentId}` : ''}`),

  generateQuiz: (topicId) =>
    request('/quiz/generate', { method: 'POST', body: { topic_id: topicId } }),
  submitQuiz: (quizId, answers) =>
    request('/quiz/submit', { method: 'POST', body: { quiz_id: quizId, answers } }),
  explainAnswer: (quizId, questionIndex) =>
    request(`/quiz/${quizId}/explain-answer/${questionIndex}`),

  generateStudyKit: (topicId) =>
    request('/study-kit/generate-advanced', { method: 'POST', body: { topic_id: topicId } }),

  requestRemediation: (topicId, subConcept) =>
    request('/remediation/micro-module', { method: 'POST', body: { topic_id: topicId, sub_concept: subConcept } }),

  sendChatMessage: (message) => request('/chat/message', { method: 'POST', body: { message } }),
  chatHistory: () => request('/chat/history'),

  progressTrends: () => request('/progress/trends'),
  progressCohort: () => request('/progress/cohort'),
}

export { ApiError, getToken }
