interface Props {
  emoji?: string
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export default function EmptyState({ emoji = '✨', title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
      <div className="text-6xl mb-5 select-none">{emoji}</div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      {description && (
        <p className="text-slate-500 text-sm max-w-xs leading-relaxed">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-6 px-6 py-2.5 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white rounded-xl font-medium text-sm transition-all duration-200"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
