// API base URL:
//  - VITE_API_BASE_URL if set at build time (separate frontend/backend hosting)
//  - otherwise same origin in production builds (backend serves the app)
//  - otherwise http://localhost:8000 for `npm run dev`
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '')

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

async function request(path, { method = 'GET', body, isForm = false, auth = true, raw = false } = {}) {
  const headers = {}
  if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? (isForm ? body : JSON.stringify(body)) : undefined,
  })

  if (raw && res.ok) return res

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

const qs = (params) => {
  const s = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''))
  return s.toString() ? `?${s}` : ''
}

export const api = {
  base: API_BASE,
  publicConfig: () => request('/config/public', { auth: false }),

  // auth
  signup: (payload) => request('/auth/signup', { method: 'POST', body: payload, auth: false }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload, auth: false }),
  me: () => request('/auth/me'),
  changePassword: (current_password, new_password) =>
    request('/auth/change-password', { method: 'POST', body: { current_password, new_password } }),

  // content (faculty)
  uploadSyllabus: (file, subjectId) => {
    const form = new FormData()
    form.append('file', file)
    if (subjectId) form.append('subject_id', subjectId)
    return request('/syllabus/upload', { method: 'POST', body: form, isForm: true })
  },
  addTextContent: (subject_id, title, content) =>
    request('/syllabus/text', { method: 'POST', body: { subject_id, title, content } }),
  syllabusStatus: (documentId) => request(`/syllabus/${documentId}/status`),
  listSyllabi: () => request('/syllabus/'),
  deleteSyllabus: (documentId) => request(`/syllabus/${documentId}`, { method: 'DELETE' }),

  // subjects
  listSubjects: () => request('/subjects/'),
  createSubject: (payload) => request('/subjects/', { method: 'POST', body: payload }),
  updateSubject: (id, payload) => request(`/subjects/${id}`, { method: 'PATCH', body: payload }),
  facultyList: () => request('/subjects/faculty-list'),

  // roster
  downloadRosterTemplate: async () => {
    const res = await request('/roster/template', { raw: true })
    return res.blob()
  },
  uploadRoster: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/roster/upload', { method: 'POST', body: form, isForm: true })
  },
  rosterStudents: () => request('/roster/students'),

  // learning
  generateStudyPlan: () => request('/study-plan/generate', { method: 'POST' }),
  getStudyPlan: () => request('/study-plan/'),
  listTopics: (documentId) => request(`/topics/${qs({ document_id: documentId })}`),
  generateQuiz: (topicId) => request('/quiz/generate', { method: 'POST', body: { topic_id: topicId } }),
  submitQuiz: (quizId, answers) => request('/quiz/submit', { method: 'POST', body: { quiz_id: quizId, answers } }),
  explainAnswer: (quizId, questionIndex) => request(`/quiz/${quizId}/explain-answer/${questionIndex}`),
  generateStudyKit: (topicId) =>
    request('/study-kit/generate-advanced', { method: 'POST', body: { topic_id: topicId } }),
  requestRemediation: (topicId, subConcept) =>
    request('/remediation/micro-module', { method: 'POST', body: { topic_id: topicId, sub_concept: subConcept } }),

  // Elara chat
  sendChatMessage: (message) => request('/chat/message', { method: 'POST', body: { message } }),
  chatHistory: () => request('/chat/history'),
  chatQuota: () => request('/chat/quota'),
  redeemChat: () => request('/chat/redeem', { method: 'POST' }),

  // student activity & rewards
  heartbeat: () => request('/activity/heartbeat', { method: 'POST' }),
  myActivity: () => request('/activity/me'),
  myRewards: () => request('/rewards/me'),
  progressTrends: () => request('/progress/trends'),
  progressCohort: () => request('/progress/cohort'),

  // faculty dashboard (limited metrics)
  facultyStudents: (subjectId) => request(`/faculty-dashboard/students${qs({ subject_id: subjectId })}`),
  facultySubjects: () => request('/faculty-dashboard/subjects'),
  facultyStudentDetail: (id) => request(`/faculty-dashboard/students/${id}`),

  // management analytics
  mgmtOverview: () => request('/analytics/overview'),
  mgmtClasses: () => request('/analytics/classes'),
  mgmtSubjects: (elective) => request(`/analytics/subjects${qs({ elective })}`),
  mgmtFaculty: () => request('/analytics/faculty'),
  mgmtStudents: (filters = {}) => request(`/analytics/students${qs(filters)}`),
  mgmtStudentDetail: (id) => request(`/analytics/students/${id}`),
}

export { ApiError, getToken }
