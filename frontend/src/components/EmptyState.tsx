interface Props {
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export default function EmptyState({ title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      {/* Inline SVG illustration */}
      <svg
        className="w-32 h-32 mb-6 text-indigo-200 dark:text-indigo-900"
        viewBox="0 0 200 200"
        fill="none"
        aria-hidden="true"
      >
        <circle cx="100" cy="100" r="90" fill="currentColor" opacity="0.3" />
        <circle cx="100" cy="80" r="30" fill="currentColor" opacity="0.5" />
        <path d="M40 160 Q100 120 160 160" stroke="currentColor" strokeWidth="4" fill="none" opacity="0.5" />
        <circle cx="70" cy="90" r="5" fill="currentColor" opacity="0.8" />
        <circle cx="130" cy="90" r="5" fill="currentColor" opacity="0.8" />
        <path d="M80 105 Q100 118 120 105" stroke="currentColor" strokeWidth="3" fill="none" opacity="0.8" />
      </svg>
      <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-2">{title}</h3>
      {description && (
        <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-6 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium text-sm transition"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
