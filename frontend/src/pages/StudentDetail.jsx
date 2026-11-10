import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import StudentReport from '../components/StudentReport'
import { Loading } from '../components/ui'

// Drill-down for one student. mode="faculty" (limited, own subjects) or "management" (full).
export default function StudentDetail({ mode }) {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetcher = mode === 'management' ? api.mgmtStudentDetail : api.facultyStudentDetail
    fetcher(id).then(setData).catch((e) => setError(e.message || 'Could not load this student'))
  }, [id, mode])

  const back = mode === 'management' ? '/management?tab=students' : '/faculty'
  if (error) return <Loading>{error}</Loading>
  if (!data) return <Loading />

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      <Link to={back} className="text-sm text-[var(--color-indigo)] mb-4 inline-block">← Back</Link>
      <StudentReport data={data} />
    </div>
  )
}
