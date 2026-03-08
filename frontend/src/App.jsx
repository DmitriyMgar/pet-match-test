import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import EvaluatePage from './pages/EvaluatePage'

function AdminPage() {
  return (
    <div className="text-center py-20">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Админка</h1>
      <p className="text-lg text-gray-600">Статистика и управление правилами</p>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm">
          <div className="max-w-5xl mx-auto px-4 py-3 flex gap-6">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `font-medium ${isActive ? 'text-indigo-600' : 'text-gray-600 hover:text-gray-900'}`
              }
            >
              Анкета
            </NavLink>
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `font-medium ${isActive ? 'text-indigo-600' : 'text-gray-600 hover:text-gray-900'}`
              }
            >
              Админка
            </NavLink>
          </div>
        </nav>

        <main className="max-w-5xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<EvaluatePage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
