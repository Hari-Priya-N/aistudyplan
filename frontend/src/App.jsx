import { Navigate, Route, Routes } from 'react-router-dom'
import Nav from './components/Nav'
import ProtectedRoute from './components/ProtectedRoute'
import { useAuth, homePathFor } from './context/AuthContext'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Chat from './pages/Chat'
import Quiz from './pages/Quiz'
import StudyKit from './pages/StudyKit'
import Progress from './pages/Progress'
import Rewards from './pages/Rewards'
import Roster from './pages/Roster'
import FacultyDashboard from './pages/FacultyDashboard'
import ManagementDashboard from './pages/ManagementDashboard'
import StudentDetail from './pages/StudentDetail'
import Account from './pages/Account'

const STUDENT = 'student'
const FACULTY = 'instructor'
const MANAGEMENT = 'management'

const guard = (element, roles) => <ProtectedRoute requireRole={roles}>{element}</ProtectedRoute>

// "/" sends each role to its own home view.
function Home() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user && user.role !== STUDENT) return <Navigate to={homePathFor(user)} replace />
  return guard(<Dashboard />, STUDENT)
}

export default function App() {
  return (
    <div className="min-h-screen bg-[var(--color-paper)] text-[var(--color-ink)]">
      <Nav />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Student view */}
        <Route path="/" element={<Home />} />
        <Route path="/quiz/:topicId" element={guard(<Quiz />)} />
        <Route path="/study-kit/:topicId" element={guard(<StudyKit />)} />
        <Route path="/progress" element={guard(<Progress />, STUDENT)} />
        <Route path="/rewards" element={guard(<Rewards />, STUDENT)} />

        {/* Shared */}
        <Route path="/chat" element={guard(<Chat />, [STUDENT, FACULTY])} />
        <Route path="/upload" element={guard(<Upload />)} />
        <Route path="/account" element={guard(<Account />)} />

        {/* Faculty view */}
        <Route path="/faculty" element={guard(<FacultyDashboard />, [FACULTY, MANAGEMENT])} />
        <Route path="/faculty/students/:id" element={guard(<StudentDetail mode="faculty" />, [FACULTY, MANAGEMENT])} />
        <Route path="/roster" element={guard(<Roster />, [FACULTY, MANAGEMENT])} />

        {/* Management view */}
        <Route path="/management" element={guard(<ManagementDashboard />, MANAGEMENT)} />
        <Route path="/management/students/:id" element={guard(<StudentDetail mode="management" />, MANAGEMENT)} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}
