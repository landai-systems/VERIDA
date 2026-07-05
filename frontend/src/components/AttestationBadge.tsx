type Status = 'passed' | 'failed' | 'pending'

const config: Record<Status, { label: string; icon: string; classes: string }> = {
  passed: {
    label: 'Human-verified',
    icon: '✓',
    classes: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  },
  failed: {
    label: 'Unverified',
    icon: '⚠',
    classes: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  },
  pending: {
    label: 'Pending',
    icon: '⏳',
    classes: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  },
}

interface Props { status: Status }

export default function AttestationBadge({ status }: Props) {
  const { label, icon, classes } = config[status]
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${classes}`}>
      <span aria-hidden="true">{icon}</span>
      {label}
    </span>
  )
}
