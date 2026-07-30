import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { Button } from './Button.jsx'

const ICONS = {
  positive: CheckCircle2,
  critical: XCircle,
  caution: AlertTriangle,
  informative: Info,
  neutral: Info,
}

const ToastContext = createContext(null)

/**
 * Toast — transient confirmation, never a place to put anything critical.
 *
 * The region is aria-live="polite" and never takes focus, so an announcement
 * can't interrupt what the user is typing. Timers pause on hover and focus,
 * because a toast that vanishes while you're reaching for its Undo is worse
 * than no toast at all.
 */
export function ToastProvider({ children, duration = 4000, max = 4 }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef(new Map())

  const dismiss = useCallback((id) => {
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const schedule = useCallback(
    (id, ms) => {
      if (!ms) return
      const existing = timers.current.get(id)
      if (existing) clearTimeout(existing)
      timers.current.set(id, setTimeout(() => dismiss(id), ms))
    },
    [dismiss],
  )

  const toast = useCallback(
    ({ title, description, variant = 'neutral', duration: ownDuration, action, persist = false }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      const ms = persist ? 0 : (ownDuration ?? duration)

      setToasts((current) => [...current, { id, title, description, variant, action, ms }].slice(-max))
      schedule(id, ms)
      return id
    },
    [duration, max, schedule],
  )

  const timersRef = timers
  useEffect(() => () => timersRef.current.forEach(clearTimeout), [timersRef])

  const api = useMemo(
    () => ({
      toast,
      dismiss,
      success: (title, opts) => toast({ ...opts, title, variant: 'positive' }),
      error: (title, opts) => toast({ ...opts, title, variant: 'critical' }),
      warning: (title, opts) => toast({ ...opts, title, variant: 'caution' }),
      info: (title, opts) => toast({ ...opts, title, variant: 'informative' }),
    }),
    [toast, dismiss],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      {createPortal(
        <div className="ds ds-toast-region" role="region" aria-label="Notifications">
          <div aria-live="polite" aria-atomic="false" className="ds-stack ds-stack--2">
            {toasts.map((t) => (
              <Toast
                key={t.id}
                {...t}
                onDismiss={() => dismiss(t.id)}
                onPause={() => {
                  const timer = timers.current.get(t.id)
                  if (timer) clearTimeout(timer)
                }}
                onResume={() => schedule(t.id, t.ms)}
              />
            ))}
          </div>
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used inside a <ToastProvider>')
  return context
}

export function Toast({
  title,
  description,
  variant = 'neutral',
  action,
  onDismiss,
  onPause,
  onResume,
  className,
  ...rest
}) {
  const Icon = ICONS[variant] ?? Info

  return (
    <div
      className={clsx('ds-toast', `ds-toast--${variant}`, className)}
      onMouseEnter={onPause}
      onMouseLeave={onResume}
      onFocusCapture={onPause}
      onBlurCapture={onResume}
      {...rest}
    >
      <span className="ds-toast__icon">
        <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
      </span>

      <div className="ds-toast__content">
        {title ? <span className="ds-toast__title">{title}</span> : null}
        {description ? <span className="ds-toast__desc">{description}</span> : null}
        {action ? (
          <Button
            variant="quiet"
            size="sm"
            className="ds-toast__action"
            onClick={() => {
              action.onClick?.()
              onDismiss?.()
            }}
          >
            {action.label}
          </Button>
        ) : null}
      </div>

      <button type="button" className="ds-toast__close" onClick={onDismiss} aria-label="Dismiss notification">
        <X size={14} strokeWidth={2} aria-hidden="true" />
      </button>
    </div>
  )
}

export default ToastProvider
