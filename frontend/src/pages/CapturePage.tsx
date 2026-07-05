import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { capture as captureApi } from '../api/capture'
import CameraCapture from '../components/CameraCapture'
import AttestationBadge from '../components/AttestationBadge'

const WINDOW_SECONDS = 600 // 10 minutes

export default function CapturePage() {
  const navigate = useNavigate()
  const [captureToken, setCaptureToken] = useState<string | null>(null)
  const [momentId, setMomentId] = useState<string | null>(null)
  const [expiresAt, setExpiresAt] = useState<Date | null>(null)
  const [secondsLeft, setSecondsLeft] = useState(WINDOW_SECONDS)
  const [blob, setBlob] = useState<Blob | null>(null)
  const [mime, setMime] = useState('image/jpeg')
  const [caption, setCaption] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    captureApi.initiate()
      .then((data) => {
        setCaptureToken(data.capture_token)
        setMomentId(data.moment_id)
        const exp = new Date(data.expires_at)
        setExpiresAt(exp)
        const secs = Math.max(0, Math.floor((exp.getTime() - Date.now()) / 1000))
        setSecondsLeft(secs)
      })
      .catch(() => setError('Failed to start capture session. Try again.'))
  }, [])

  useEffect(() => {
    if (!expiresAt) return
    timerRef.current = setInterval(() => {
      const s = Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000))
      setSecondsLeft(s)
      if (s === 0 && timerRef.current) clearInterval(timerRef.current)
    }, 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [expiresAt])

  const handleCapture = useCallback((b: Blob, mimeType: string) => {
    setBlob(b)
    setMime(mimeType)
  }, [])

  const handleFallbackText = useCallback((text: string) => {
    const b = new Blob([text], { type: 'text/plain' })
    setBlob(b)
    setMime('text/plain')
    setCaption(text)
  }, [])

  const submit = async () => {
    if (!blob || !captureToken || !momentId) return
    setSubmitting(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('moment_id', momentId)
      form.append('caption', caption)
      const ext = mime === 'text/plain' ? 'txt' : 'jpg'
      form.append('media', blob, `moment.${ext}`)
      await captureApi.submit(captureToken, form)
      setDone(true)
    } catch {
      setError('Submission failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const mins = Math.floor(secondsLeft / 60)
  const secs = secondsLeft % 60
  const expired = secondsLeft === 0

  if (done) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-screen gap-6 text-center">
        <div className="text-6xl">✨</div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Moment shared!</h2>
        <AttestationBadge status="pending" />
        <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs">
          Your moment is being verified. It will appear in your circles' feeds shortly.
        </p>
        <button
          onClick={() => navigate('/feed')}
          className="px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold transition"
        >
          View Feed
        </button>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 max-w-lg mx-auto">
      <div className="text-center pt-4">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Today's Moment</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Capture something real from right now.</p>
      </div>

      {/* Timer */}
      {captureToken && (
        <div className={`text-center font-mono text-lg font-semibold ${expired ? 'text-red-500' : 'text-indigo-600 dark:text-indigo-400'}`}
          aria-live="polite"
          aria-label="Time remaining">
          {expired ? 'Window expired' : `${mins}:${secs.toString().padStart(2, '0')} remaining`}
        </div>
      )}

      {error && (
        <p role="alert" className="text-sm text-red-500 dark:text-red-400 text-center">{error}</p>
      )}

      {!blob ? (
        <CameraCapture onCapture={handleCapture} onFallbackText={handleFallbackText} />
      ) : (
        <div className="space-y-4">
          {mime !== 'text/plain' && blob && (
            <img
              src={URL.createObjectURL(blob)}
              alt="Captured moment"
              className="w-full rounded-xl object-cover max-h-80"
            />
          )}
          <div>
            <label htmlFor="caption" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
              Caption (optional)
            </label>
            <textarea
              id="caption"
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              className="w-full h-24 bg-slate-100 dark:bg-slate-800 rounded-xl p-3 text-sm resize-none outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="What's happening right now?"
              maxLength={500}
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setBlob(null)}
              className="flex-1 py-3 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl font-medium transition"
            >
              Retake
            </button>
            <button
              onClick={submit}
              disabled={submitting || expired}
              className="flex-2 px-8 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-semibold transition"
            >
              {submitting ? 'Sharing…' : 'Share Moment'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
