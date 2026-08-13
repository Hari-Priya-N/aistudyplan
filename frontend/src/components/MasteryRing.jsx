// Signature element: a mastery ring rather than a generic progress bar,
// echoing the doc's "knowledge-gap dashboard" / knowledge-graph framing.
export default function MasteryRing({ score = 0, size = 56, label }) {
  const radius = (size - 8) / 2
  const circumference = 2 * Math.PI * radius
  const clamped = Math.max(0, Math.min(1, score))
  const offset = circumference * (1 - clamped)

  const color =
    clamped >= 0.75 ? 'var(--color-forest)' : clamped >= 0.4 ? 'var(--color-gold)' : 'var(--color-rust)'

  return (
    <div className="flex flex-col items-center gap-1" role="img" aria-label={`Mastery ${Math.round(clamped * 100)}%`}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ '--ring-circumference': circumference, '--ring-offset': offset }}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-line)"
          strokeWidth="6"
        />
        <circle
          className="mastery-ring-progress"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="central"
          fontFamily="var(--font-mono)"
          fontSize={size * 0.26}
          fill="var(--color-ink)"
        >
          {Math.round(clamped * 100)}
        </text>
      </svg>
      {label && <span className="text-xs text-[var(--color-ink-soft)] text-center max-w-24 truncate">{label}</span>}
    </div>
  )
}
