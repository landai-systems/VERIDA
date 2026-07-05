import { useState } from 'react'
import AttestationBadge from './AttestationBadge'
import ReactionBar from './ReactionBar'
import CommentSection from './CommentSection'
import { Post } from '../api/feed'

interface Props { post: Post }

export default function PostCard({ post }: Props) {
  const [showComments, setShowComments] = useState(false)

  const status = post.attestation_status === 'passed'
    ? 'passed'
    : post.attestation_status === 'failed'
    ? 'failed'
    : 'pending'

  const formattedDate = new Date(post.published_at).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })

  return (
    <article className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 p-4">
        <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-bold text-sm overflow-hidden">
          {post.author_avatar_url ? (
            <img src={post.author_avatar_url} alt={post.author_display_name} className="w-full h-full object-cover" />
          ) : (
            post.author_display_name.slice(0, 2).toUpperCase()
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm truncate">{post.author_display_name}</p>
          <p className="text-slate-400 text-xs">@{post.author_handle} · {formattedDate}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {post.is_late && (
            <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 px-2 py-0.5 rounded-full">Late</span>
          )}
          <AttestationBadge status={status} />
        </div>
      </div>

      {/* Media */}
      {post.media_url && (
        <img
          src={post.media_url}
          alt={post.caption || 'Moment'}
          className="w-full object-cover max-h-80"
          loading="lazy"
        />
      )}

      {/* Caption */}
      {post.caption && (
        <p className="px-4 pt-3 text-sm text-slate-700 dark:text-slate-300">{post.caption}</p>
      )}

      {/* Reactions + comments toggle */}
      <div className="px-4 py-3 flex items-center justify-between">
        <ReactionBar postId={post.id} myReactions={post.my_reactions} />
        <button
          onClick={() => setShowComments(!showComments)}
          className="text-xs text-slate-500 hover:text-indigo-500 transition"
          aria-expanded={showComments}
          aria-controls={`comments-${post.id}`}
        >
          💬 Comment
        </button>
      </div>

      {/* Comments */}
      {showComments && (
        <div id={`comments-${post.id}`} className="px-4 pb-4 border-t border-slate-100 dark:border-slate-800 pt-3">
          <CommentSection postId={post.id} initialComments={[]} />
        </div>
      )}
    </article>
  )
}
