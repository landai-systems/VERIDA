import { useState } from 'react'
import { reactions as reactionsApi } from '../api/reactions'
import { useFeedStore } from '../store/feedStore'

const EMOJIS = ['❤️', '😊', '🔥', '🌟', '🤗'] as const

interface Props {
  postId: string
  myReactions: string[]
}

export default function ReactionBar({ postId, myReactions }: Props) {
  const updatePostReaction = useFeedStore((s) => s.updatePostReaction)
  const [pending, setPending] = useState<string | null>(null)

  const toggle = async (emoji: string) => {
    if (pending) return
    const has = myReactions.includes(emoji)
    setPending(emoji)
    try {
      if (has) {
        await reactionsApi.remove(postId, emoji)
        updatePostReaction(postId, emoji, false)
      } else {
        await reactionsApi.add(postId, emoji)
        updatePostReaction(postId, emoji, true)
      }
    } catch {
      /* ignore */
    } finally {
      setPending(null)
    }
  }

  return (
    <div
      className="flex items-center gap-1.5 bg-white/5 rounded-full px-3 py-1.5"
      role="group"
      aria-label="Reactions"
    >
      {EMOJIS.map((emoji) => {
        const active = myReactions.includes(emoji)
        return (
          <button
            key={emoji}
            onClick={() => toggle(emoji)}
            disabled={pending === emoji}
            className={`text-xl transition-all duration-150 select-none rounded-full px-1.5 py-0.5 ${
              active
                ? 'bg-indigo-500/20 border border-indigo-500/40 scale-105'
                : 'hover:scale-110 hover:bg-white/10'
            } active:scale-95`}
            aria-pressed={active}
            aria-label={`React with ${emoji}`}
          >
            {emoji}
          </button>
        )
      })}
    </div>
  )
}
