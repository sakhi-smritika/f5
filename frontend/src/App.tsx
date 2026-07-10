import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute, PublicRoute } from './components/ProtectedRoute'
import { DiaryPage } from './pages/DiaryPage'
import { LoginPage } from './pages/LoginPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/introspection/diary" element={<DiaryPage />} />
            <Route path="/" element={<Navigate to="/introspection/diary" replace />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
