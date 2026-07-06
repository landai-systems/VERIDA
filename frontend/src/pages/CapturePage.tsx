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
  const [mode, setMode] = useState<'photo' | 'text'>('photo')
  const [textContent, setTextContent] = useState('')
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    captureApi
      .initiate()
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
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
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
    if (!captureToken || !momentId) return
    // For text mode
    const finalBlob =
      mode === 'text'
        ? new Blob([textContent], { type: 'text/plain' })
        : blob

    if (!finalBlob) return
    setSubmitting(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('moment_id', momentId)
      form.append('caption', mode === 'text' ? textContent : caption)
      const ext = mime === 'text/plain' || mode === 'text' ? 'txt' : 'jpg'
      form.append('media', finalBlob, `moment.${ext}`)
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
  const progress = ((WINDOW_SECONDS - secondsLeft) / WINDOW_SECONDS) * 100

  if (done) {
    return (
      <div className="fixed inset-0 bg-[#080810] flex flex-col items-center justify-center gap-6 text-center px-6">
        <div className="text-7xl select-none">✨</div>
        <h2 className="text-2xl font-bold text-white">Moment shared!</h2>
        <AttestationBadge status="pending" />
        <p className="text-slate-400 text-sm max-w-xs leading-relaxed">
          Your moment is being verified. It will appear in your circles' feeds shortly.
        </p>
        <button
          onClick={() => navigate('/feed')}
          className="px-8 py-3 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white rounded-xl font-semibold transition-all duration-200"
        >
          View Feed
        </button>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-[#080810] flex flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 pt-safe pt-4 h-14 flex-shrink-0 relative">
        <button
          onClick={() => navigate(-1)}
          className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center text-white hover:bg-white/20 transition-colors"
          aria-label="Close"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <span className="absolute left-1/2 -translate-x-1/2 text-white font-black text-lg tracking-tight">VERIDA</span>

        {/* Mode toggle */}
        <div className="flex items-center bg-white/10 rounded-full p-0.5 gap-0.5">
          <button
            onClick={() => setMode('photo')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all duration-150 ${
              mode === 'photo' ? 'bg-white text-black' : 'text-white/70 hover:text-white'
            }`}
          >
            📷 Photo
          </button>
          <button
            onClick={() => setMode('text')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all duration-150 ${
              mode === 'text' ? 'bg-white text-black' : 'text-white/70 hover:text-white'
            }`}
          >
            ✍️ Text
          </button>
        </div>
      </div>

      {/* Timer progress bar */}
      {captureToken && (
        <div className="flex-shrink-0">
          <div className="h-0.5 bg-white/10">
            <div
              className={`h-full transition-all duration-1000 ${
                expired ? 'bg-red-500' : 'bg-gradient-to-r from-indigo-500 to-violet-500'
              }`}
              style={{ width: `${expired ? 100 : progress}%` }}
            />
          </div>
          <div className="text-center mt-1.5 mb-1">
            <span
              className={`text-xs font-mono font-semibold ${expired ? 'text-red-400' : 'text-indigo-400'}`}
              aria-live="polite"
            >
              {expired ? 'Window expired' : `${mins}:${secs.toString().padStart(2, '0')} remaining`}
            </span>
          </div>
        </div>
      )}

      {/* Main capture area */}
      <div className="flex-1 relative overflow-hidden">
        {mode === 'photo' ? (
          !blob ? (
            <div className="w-full h-full">
              <CameraCapture onCapture={handleCapture} onFallbackText={handleFallbackText} />
            </div>
          ) : (
            <div className="w-full h-full flex flex-col">
              {/* Preview */}
              <div className="flex-1 overflow-hidden">
                <img
                  src={URL.createObjectURL(blob)}
                  alt="Captured moment"
                  className="w-full h-full object-cover"
                />
              </div>
              {/* Caption + submit */}
              <div className="flex-shrink-0 bg-gradient-to-t from-black/80 to-transparent p-4 space-y-3 absolute bottom-0 left-0 right-0">
                <textarea
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  className="w-full bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl px-4 py-3 text-white placeholder-slate-400 text-sm resize-none outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  placeholder="Add a caption…"
                  rows={2}
                  maxLength={500}
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => setBlob(null)}
                    className="flex-none px-5 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-medium text-sm transition-colors backdrop-blur-sm"
                  >
                    Retake
                  </button>
                  <button
                    onClick={submit}
                    disabled={submitting || expired}
                    className="flex-1 py-3 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2"
                  >
                    {submitting ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                        Sharing…
                      </>
                    ) : (
                      'Share Moment'
                    )}
                  </button>
                </div>
              </div>
            </div>
          )
        ) : (
          /* Text mode */
          <div className="flex flex-col h-full p-4 gap-4">
            <textarea
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              autoFocus
              className="flex-1 bg-transparent text-white text-xl font-medium placeholder-slate-600 resize-none outline-none leading-relaxed"
              placeholder="What's happening right now?"
              maxLength={500}
            />
            <div className="flex items-center justify-between">
              <span className="text-slate-600 text-xs">{textContent.length}/500</span>
              <button
                onClick={submit}
                disabled={submitting || expired || !textContent.trim()}
                className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-all duration-200 flex items-center gap-2"
              >
                {submitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Sharing…
                  </>
                ) : (
                  'Share Moment'
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Shutter button (photo mode, no capture yet) */}
      {mode === 'photo' && !blob && (
        <div className="flex-shrink-0 flex items-center justify-center pb-safe pb-8 pt-4 h-28">
          <div className="text-center">
            <p className="text-slate-500 text-xs mb-3">Use the camera preview above to capture</p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="absolute top-20 left-4 right-4 z-50">
          <div className="bg-red-500/20 border border-red-500/30 text-red-400 rounded-2xl px-4 py-3 text-sm text-center backdrop-blur-sm">
            {error}
          </div>
        </div>
      )}
    </div>
  )
}
