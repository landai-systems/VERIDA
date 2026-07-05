import { useState, useRef, useCallback, useEffect } from 'react'

interface Props {
  onCapture: (blob: Blob, mimeType: string) => void
  onFallbackText: (text: string) => void
}

export default function CameraCapture({ onCapture, onFallbackText }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'camera' | 'text'>('camera')
  const [text, setText] = useState('')
  const [preview, setPreview] = useState<string | null>(null)

  const startCamera = useCallback(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      setStream(s)
      if (videoRef.current) {
        videoRef.current.srcObject = s
      }
      setError(null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Camera unavailable'
      setError(msg)
      setMode('text')
    }
  }, [])

  useEffect(() => {
    if (mode === 'camera') startCamera()
    return () => {
      stream?.getTracks().forEach((t) => t.stop())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode])

  const capture = () => {
    if (!videoRef.current) return
    const canvas = document.createElement('canvas')
    canvas.width = videoRef.current.videoWidth
    canvas.height = videoRef.current.videoHeight
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(videoRef.current, 0, 0)
    canvas.toBlob((blob) => {
      if (!blob) return
      setPreview(URL.createObjectURL(blob))
      onCapture(blob, 'image/jpeg')
      stream?.getTracks().forEach((t) => t.stop())
    }, 'image/jpeg', 0.9)
  }

  if (preview) {
    return (
      <div className="relative">
        <img src={preview} alt="Preview" className="w-full rounded-xl object-cover max-h-96" />
        <button
          onClick={() => { setPreview(null); setMode('camera') }}
          className="absolute top-2 right-2 bg-black/50 text-white rounded-full px-3 py-1 text-sm"
        >
          Retake
        </button>
      </div>
    )
  }

  if (mode === 'text') {
    return (
      <div className="space-y-3">
        {error && (
          <p className="text-amber-600 dark:text-amber-400 text-sm text-center">
            📷 Camera unavailable — share in words instead.
          </p>
        )}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe your moment in a few words…"
          className="w-full h-40 bg-slate-100 dark:bg-slate-800 rounded-xl p-4 text-sm resize-none outline-none focus:ring-2 focus:ring-indigo-500"
          aria-label="Moment description"
          maxLength={500}
        />
        <div className="flex justify-between text-xs text-slate-400">
          <button onClick={() => setMode('camera')} className="text-indigo-500 hover:underline">Use camera instead</button>
          <span>{text.length}/500</span>
        </div>
        <button
          onClick={() => onFallbackText(text)}
          disabled={!text.trim()}
          className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-medium transition"
        >
          Use this description
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="relative bg-black rounded-xl overflow-hidden aspect-video">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
          aria-label="Camera preview"
        />
      </div>
      <div className="flex gap-3">
        <button
          onClick={capture}
          className="flex-1 py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold text-lg transition active:scale-95"
          aria-label="Take photo"
        >
          📸 Capture
        </button>
        <button
          onClick={() => setMode('text')}
          className="px-4 py-4 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-sm transition"
          aria-label="Use text instead"
        >
          Text
        </button>
      </div>
      <p className="text-center text-xs text-slate-400">Gallery uploads are not accepted — capture this moment live.</p>
    </div>
  )
}
