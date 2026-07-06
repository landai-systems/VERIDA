interface Props {
  count: number
  size?: 'sm' | 'md'
}

export default function StreakBadge({ count, size = 'md' }: Props) {
  if (count === 0) return null
  const big = size === 'md'
  const pulse = count > 7

  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold rounded-full bg-orange-500/20 border border-orange-500/30 text-orange-400 ${
        big ? 'text-base px-3 py-1' : 'text-sm px-2 py-0.5'
      } ${pulse ? 'animate-pulse' : ''}`}
      aria-label={`${count} day streak`}
    >
      🔥 {count}
    </span>
  )
}
