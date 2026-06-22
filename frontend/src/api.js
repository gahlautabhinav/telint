export const api = {
  getTargets: () => fetch('/api/targets').then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); }),
  addTarget: (body) => fetch('/api/targets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); }),
  deleteTarget: (handle) => fetch(`/api/targets/${handle}`, {
    method: 'DELETE'
  }).then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.status === 204 ? {} : r.json(); }),
  getMembers: (handle) => fetch(`/api/targets/${handle}/members`).then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); }),
  scrape: (body) => fetch('/api/scrape', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); }),
  setMonitor: (body) => fetch('/api/monitor', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); }),
  exportData: (handle, format) => `/api/export/${handle}?format=${format}`,
  getMessages: (handle, limit) => {
    const url = limit != null ? `/api/targets/${handle}/messages?limit=${limit}` : `/api/targets/${handle}/messages`
    return fetch(url).then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); })
  },
  scrapeMessages: (handle, limit) => fetch('/api/scrape', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ handle, mode: 'messages', ...(limit != null ? { limit } : {}) })
  }).then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); }),
  scrapeAdmins: (handle) => fetch('/api/scrape', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ handle, mode: 'admins' })
  }).then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); }),
}
