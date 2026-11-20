import { useEffect, useRef, useState } from 'react'
import { BrowserQRCodeReader } from '@zxing/browser'
import { ErrorState, LoadingState } from './FeedbackStates.jsx'
import './QrScannerDialog.css'

export function QrScannerDialog({ onScan, onClose }) {
  const dialogRef = useRef(null)
  const videoRef = useRef(null)
  const onScanRef = useRef(onScan)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    onScanRef.current = onScan
  }, [onScan])

  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog && !dialog.open) dialog.showModal()
    return () => {
      if (dialog?.open) dialog.close()
    }
  }, [])

  useEffect(() => {
    let active = true
    let controls
    const reader = new BrowserQRCodeReader()

    reader
      .decodeFromVideoDevice(undefined, videoRef.current, (result, _decodeError, scannerControls) => {
        controls = scannerControls
        if (result && active) {
          scannerControls.stop()
          onScanRef.current(result.getText())
        }
      })
      .then((scannerControls) => {
        controls = scannerControls
        if (active) setLoading(false)
        if (!active) scannerControls.stop()
      })
      .catch((cameraError) => {
        if (active) {
          setLoading(false)
          setError(
            cameraError.message ||
              'Kamera açılamadı. Tarayıcı ayarlarından kamera izni verin.',
          )
        }
      })

    return () => {
      active = false
      controls?.stop()
    }
  }, [retryKey])

  function retryCamera() {
    setLoading(true)
    setError('')
    setRetryKey((key) => key + 1)
  }

  return (
    <dialog
      aria-labelledby="qr-scanner-title"
      className="qr-scanner-dialog"
      onCancel={onClose}
      onClose={onClose}
      ref={dialogRef}
    >
      <div className="qr-scanner-header">
        <h2 id="qr-scanner-title">Sipariş QR kodunu okut</h2>
        <button
          aria-label="Kamera penceresini kapat"
          className="button-secondary"
          onClick={onClose}
          type="button"
        >
          ×
        </button>
      </div>
      <video aria-label="QR kod kamerası" autoPlay muted playsInline ref={videoRef} />
      {error ? (
        <ErrorState
          message={error}
          onRetry={retryCamera}
          retrying={loading}
        />
      ) : loading ? (
        <LoadingState message="Kamera açılıyor…" />
      ) : (
        <p className="muted">Kamerayı sipariş QR koduna doğrultun.</p>
      )}
    </dialog>
  )
}
