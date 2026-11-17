/** "Speak your turn": the browser's built-in speech recognition (Chrome, Edge; partly Safari).
 * Nothing is sent to our server or to the AI models; where it's unsupported, the button is hidden. */
import { useCallback, useEffect, useRef, useState } from 'react'

interface RecognitionResult {
  isFinal: boolean
  0: { transcript: string }
}
interface RecognitionEvent {
  resultIndex: number
  results: ArrayLike<RecognitionResult>
}
interface Recognition {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((e: RecognitionEvent) => void) | null
  onend: (() => void) | null
  onerror: ((e: { error: string }) => void) | null
  start(): void
  stop(): void
}
type RecognitionCtor = new () => Recognition

function getCtor(): RecognitionCtor | undefined {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition
}

export const speechSupported = typeof window !== 'undefined' && !!getCtor()

/** onFinal receives each finished phrase; `interim` is the phrase still being heard. */
export function useSpeech(onFinal: (text: string) => void) {
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const [error, setError] = useState<string | null>(null)
  const rec = useRef<Recognition | null>(null)
  const final = useRef(onFinal)
  useEffect(() => {
    final.current = onFinal
  }, [onFinal])

  const stop = useCallback(() => {
    rec.current?.stop()
  }, [])

  const start = useCallback(() => {
    const Ctor = getCtor()
    if (!Ctor) return
    const r = new Ctor()
    r.lang = navigator.language || 'en-IN'
    r.continuous = true
    r.interimResults = true
    r.onresult = (e) => {
      let pending = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i]
        if (res.isFinal) final.current(res[0].transcript.trim())
        else pending += res[0].transcript
      }
      setInterim(pending)
    }
    r.onerror = (e) => {
      setError(e.error === 'not-allowed' ? 'Microphone access was blocked.' : 'Speech input stopped.')
    }
    r.onend = () => {
      setListening(false)
      setInterim('')
      rec.current = null
    }
    rec.current = r
    setError(null)
    setListening(true)
    r.start()
  }, [])

  useEffect(() => () => rec.current?.stop(), [])
  return { listening, interim, error, start, stop }
}
