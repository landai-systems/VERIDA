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
        className="absolute inset-0 bg-black/60 backdrop-blur-md"
        onClick={onDismiss}
        aria-hidden="true"
      />
      {/* Card */}
      <div className="relative backdrop-blur-xl bg-white/5 border border-white/10 rounded-3xl p-8 max-w-sm w-full shadow-[0_0_40px_rgba(99,102,241,0.15)] text-center">
        <div className="text-5xl mb-4 select-none">🌿</div>
        <h2 id="nudge-title" className="text-lg font-semibold text-white mb-2">
          You've been here a while.
        </h2>
        <p className="text-slate-400 text-sm mb-6 leading-relaxed">
          Take a break? The feed will be here when you return. Your well-being matters more than the scroll.
        </p>
        <button
          onClick={onDismiss}
          className="w-full py-3 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white rounded-xl font-semibold transition-all duration-200"
        >
          Thanks, I'll take a break
        </button>
        <button
          onClick={onDismiss}
          className="mt-3 w-full py-2 text-slate-500 text-sm hover:text-slate-300 transition-colors"
        >
          Stay a bit longer
        </button>
      </div>
    </div>
  )
}
