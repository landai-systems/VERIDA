type Status = 'passed' | 'failed' | 'pending'

const config: Record<Status, { label: string; icon: string; classes: string }> = {
  passed: {
    label: 'Verified',
    icon: '✓',
    classes:
      'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  },
  failed: {
    label: 'Flagged',
    icon: '⚠',
    classes:
      'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  },
  pending: {
    label: 'Pending',
    icon: '',
    classes:
      'bg-slate-500/20 text-slate-400 border border-slate-500/30',
  },
}

interface Props {
  status: Status
}

export default function AttestationBadge({ status }: Props) {
  const { label, icon, classes } = config[status]
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${classes}`}
    >
      {status === 'pending' ? (
        <span className="w-3 h-3 border border-slate-400 border-t-transparent rounded-full animate-spin" aria-hidden="true" />
      ) : (
        <span aria-hidden="true">{icon}</span>
      )}
      {label}
    </span>
  )
}
