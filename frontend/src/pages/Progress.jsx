import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import StudentReport from '../components/StudentReport'
import { Loading } from '../components/ui'

// Student's own view of their activity: logins, sessions, scores, improvement.
export default function Progress() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.myActivity().then(setData).catch(() => setError('Could not load your progress right now.'))
  }, [])

  if (error) return <Loading>{error}</Loading>
  if (!data) return <Loading>Loading progress…</Loading>

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      <StudentReport
        data={data}
        title="My progress"
        subtitle="Your logins, study sessions, and how your scores have moved since each pre-assessment."
        self
      />
      {data.topics.length === 0 && (
        <p className="text-sm text-[var(--color-ink-soft)] mt-4">
          Take a pre-assessment from <Link to="/" className="text-[var(--color-indigo)] font-medium">My path</Link> to start tracking.
        </p>
      )}
    </div>
  )
}
