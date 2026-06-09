export const api = {
  getTargets: () => fetch('/api/targets').then(r => r.json()),
  addTarget: (body) => fetch('/api/targets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => r.json()),
  deleteTarget: (handle) => fetch(`/api/targets/${handle}`, {
    method: 'DELETE'
  }).then(r => r.json()),
  getMembers: (handle) => fetch(`/api/targets/${handle}/members`).then(r => r.json()),
  scrape: (body) => fetch('/api/scrape', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => r.json()),
  setMonitor: (body) => fetch('/api/monitor', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => r.json()),
  exportData: (handle, format) => `/api/export/${handle}?format=${format}`,
}
