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
    } catch { /* ignore */ } finally {
      setPending(null)
    }
  }

  return (
    <div className="flex gap-1" role="group" aria-label="Reactions">
      {EMOJIS.map((emoji) => {
        const active = myReactions.includes(emoji)
        return (
          <button
            key={emoji}
            onClick={() => toggle(emoji)}
            disabled={pending === emoji}
            className={`text-xl p-1.5 rounded-full transition-transform hover:scale-110 active:scale-95 ${
              active ? 'bg-indigo-100 dark:bg-indigo-900/40 ring-2 ring-indigo-400' : 'hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
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
