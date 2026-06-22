import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Members from './pages/Members'
import Messages from './pages/Messages'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/target/:handle" element={<Members />} />
        <Route path="/target/:handle/messages" element={<Messages />} />
      </Routes>
    </BrowserRouter>
  )
}
