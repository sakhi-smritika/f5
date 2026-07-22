import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute, PublicRoute } from './components/ProtectedRoute'
import { DayLogPage } from './pages/DayLogPage'
import { DiaryPage } from './pages/DiaryPage'
import { GoalsPage } from './pages/GoalsPage'
import { KbitsPage } from './pages/KbitsPage'
import { LoginPage } from './pages/LoginPage'
import { ProfilePage } from './pages/ProfilePage'
import { SettingsPage } from './pages/SettingsPage'

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
            <Route path="/introspection/day-log" element={<DayLogPage />} />
            <Route path="/goals" element={<GoalsPage />} />
            <Route path="/goals/:goalId" element={<GoalsPage />} />
            <Route path="/kbits" element={<KbitsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/" element={<Navigate to="/introspection/diary" replace />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
