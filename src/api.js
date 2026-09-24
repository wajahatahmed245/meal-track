const BASE = import.meta.env.VITE_API_BASE ||
  (import.meta.env.DEV ? 'http://localhost:8010/api' : '/meal/api')

function authHeaders() {
  const token = localStorage.getItem('mt_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401) {
    localStorage.removeItem('mt_token')
    window.location.reload()
    throw new Error('Unauthorized')
  }
  if (res.status === 204) return null
  const data = await res.json()
  if (!res.ok) throw Object.assign(new Error(data.detail || res.statusText), { status: res.status })
  return data
}

export const api = {
  login:   (email, password) => request('POST', '/auth/login', { email, password }),
  getMe:   ()                => request('GET',  '/user/me'),
  updateMe: (data)           => request('PATCH', '/user/me', data),

  getMeals:    (date, start, end) => {
    const params = date ? `?date=${date}` : (start ? `?start=${start}&end=${end}` : '')
    return request('GET', `/meals${params}`)
  },
  addMeal:    (data) => request('POST',  '/meals', data),
  updateMeal: (id, data) => request('PATCH', `/meals/${id}`, data),
  deleteMeal: (id)   => request('DELETE', `/meals/${id}`),

  getDrinks:    (date) => request('GET', `/drinks${date ? `?date=${date}` : ''}`),
  addDrink:    (data) => request('POST',  '/drinks', data),
  updateDrink: (id, data) => request('PATCH', `/drinks/${id}`, data),
  deleteDrink: (id)   => request('DELETE', `/drinks/${id}`),

  getExercise:    (date) => request('GET', `/exercise${date ? `?date=${date}` : ''}`),
  logExercise:    (data) => request('POST',  '/exercise', data),
  updateExercise: (id, data) => request('PATCH', `/exercise/${id}`, data),
  deleteExercise: (id)   => request('DELETE', `/exercise/${id}`),

  getTodaySummary:  ()             => request('GET', '/summary/today'),
  getDaySummary:    (date)         => request('GET', `/summary/day?day=${date}`),
  getWeeklySummary: ()             => request('GET', '/summary/weekly'),
  getRangeSummary:  (start, end)   => request('GET', `/summary/range?start=${start}&end=${end}`),
  getStats:         ()             => request('GET', '/summary/stats'),
  searchFood:       (q)            => request('GET', `/food/search?q=${encodeURIComponent(q)}`),
}
