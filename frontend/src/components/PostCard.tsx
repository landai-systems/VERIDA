import { useState } from 'react'
import AttestationBadge from './AttestationBadge'
import ReactionBar from './ReactionBar'
import CommentSection from './CommentSection'
import { Post } from '../api/feed'

interface Props {
  post: Post
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export default function PostCard({ post }: Props) {
  const [showComments, setShowComments] = useState(false)

  const status =
    post.attestation_status === 'passed'
      ? 'passed'
      : post.attestation_status === 'failed'
      ? 'failed'
      : 'pending'

  const initials = post.author_display_name.slice(0, 2).toUpperCase()

  return (
    <article className="bg-white/5 border border-white/[0.08] rounded-2xl overflow-hidden transition-all duration-200 hover:border-white/[0.12]">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 pt-4 pb-3">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500/40 to-violet-600/40 flex items-center justify-center text-white font-bold text-sm overflow-hidden flex-shrink-0 border border-white/10">
          {post.author_avatar_url ? (
            <img
              src={post.author_avatar_url}
              alt={post.author_display_name}
              className="w-full h-full object-cover"
            />
          ) : (
            initials
          )}
        </div>

        {/* Name + time */}
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-white text-sm truncate">{post.author_display_name}</p>
          <p className="text-slate-500 text-xs">
            @{post.author_handle} · {formatTime(post.published_at)}
          </p>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {post.is_late && (
            <span className="text-xs bg-orange-500/20 text-orange-400 border border-orange-500/30 px-2 py-0.5 rounded-full">
              Posted late
            </span>
          )}
          <AttestationBadge status={status} />
        </div>
      </div>

      {/* Media */}
      {post.media_url && (
        <div className="aspect-[4/5] w-full overflow-hidden">
          <img
            src={post.media_url}
            alt={post.caption || 'Moment'}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        </div>
      )}

      {/* Caption */}
      {post.caption && (
        <p className="px-4 pt-3 text-sm text-slate-300 leading-relaxed">{post.caption}</p>
      )}

      {/* Reaction bar + comment toggle */}
      <div className="px-4 py-3 flex items-center justify-between gap-3">
        <ReactionBar postId={post.id} myReactions={post.my_reactions} />
        <button
          onClick={() => setShowComments(!showComments)}
          className="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1.5"
          aria-expanded={showComments}
          aria-controls={`comments-${post.id}`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          Comment
        </button>
      </div>

      {/* Comments */}
      {showComments && (
        <div
          id={`comments-${post.id}`}
          className="px-4 pb-4 border-t border-white/[0.06] pt-3"
        >
          <CommentSection postId={post.id} initialComments={[]} />
        </div>
      )}
    </article>
  )
}
