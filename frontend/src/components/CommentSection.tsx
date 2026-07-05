import { useState } from 'react'
import { comments as commentsApi, Comment } from '../api/comments'

interface Props {
  postId: string
  initialComments: Comment[]
}

export default function CommentSection({ postId, initialComments }: Props) {
  const [items, setItems] = useState<Comment[]>(initialComments)
  const [body, setBody] = useState('')
  const [loading, setLoading] = useState(false)
  const MAX = 500

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!body.trim() || body.length > MAX) return
    setLoading(true)
    try {
      const c = await commentsApi.add(postId, body.trim())
      setItems([...items, c])
      setBody('')
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }

  const remove = async (id: string) => {
    try {
      await commentsApi.delete(postId, id)
      setItems(items.filter((c) => c.id !== id))
    } catch { /* ignore */ }
  }

  return (
    <div className="mt-3 space-y-3">
      {items.map((c) => (
        <div key={c.id} className="flex gap-2 text-sm">
          <span className="font-semibold text-slate-700 dark:text-slate-300 flex-shrink-0">@{c.author_handle}</span>
          <span className="text-slate-600 dark:text-slate-400 flex-1">{c.body}</span>
          <button
            onClick={() => remove(c.id)}
            className="text-slate-400 hover:text-red-400 text-xs flex-shrink-0"
            aria-label="Delete comment"
          >
            ×
          </button>
        </div>
      ))}

      <form onSubmit={submit} className="flex gap-2">
        <div className="flex-1 relative">
          <input
            type="text"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Add a comment…"
            maxLength={MAX}
            className="w-full bg-slate-100 dark:bg-slate-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500 pr-12"
            aria-label="Comment text"
          />
          <span className={`absolute right-2 top-2 text-xs ${body.length > MAX - 20 ? 'text-amber-500' : 'text-slate-400'}`}>
            {MAX - body.length}
          </span>
        </div>
        <button
          type="submit"
          disabled={loading || !body.trim() || body.length > MAX}
          className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition"
        >
          Post
        </button>
      </form>
    </div>
  )
}
