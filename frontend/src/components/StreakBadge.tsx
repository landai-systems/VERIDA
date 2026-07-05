interface Props {
  count: number
  size?: 'sm' | 'md'
}

export default function StreakBadge({ count, size = 'md' }: Props) {
  if (count === 0) return null
  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold text-amber-500 dark:text-amber-400 ${
        size === 'sm' ? 'text-sm' : 'text-base'
      }`}
      aria-label={`${count} day streak`}
    >
      🔥 {count}
    </span>
  )
}
