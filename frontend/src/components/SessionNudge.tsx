interface Props {
  onDismiss: () => void
}

export default function SessionNudge({ onDismiss }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="nudge-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onDismiss}
        aria-hidden="true"
      />
      {/* Card */}
      <div className="relative bg-white dark:bg-slate-900 rounded-2xl p-8 max-w-sm w-full shadow-2xl text-center">
        <div className="text-5xl mb-4">🌿</div>
        <h2 id="nudge-title" className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-2">
          You've been here a while.
        </h2>
        <p className="text-slate-500 dark:text-slate-400 text-sm mb-6">
          Take a break? The feed will be here when you return. Your well-being matters more than the scroll.
        </p>
        <button
          onClick={onDismiss}
          className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition"
        >
          Thanks, I'll take a break
        </button>
        <button
          onClick={onDismiss}
          className="mt-3 w-full py-2 text-slate-500 dark:text-slate-400 text-sm hover:text-slate-700 dark:hover:text-slate-200 transition"
        >
          Stay a bit longer
        </button>
      </div>
    </div>
  )
}
