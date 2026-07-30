import { useCallback, useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import clsx from 'clsx'
import { AlertTriangle, X } from 'lucide-react'
import { Button, IconButton } from './Button.jsx'

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Modal — scrim, focus trap, Escape to close, body scroll lock.
 *
 * Portals to <body> so no ancestor's overflow or transform can clip it, and
 * the portal node carries `ds` because the tokens live on that root class.
 *
 * Focus moves in on open and back to the trigger on close; Tab cycles inside.
 * Anything less makes the dialog a dead end for keyboard users.
 */
export function Modal({
  open,
  onClose,
  title,
  eyebrow,
  description,
  size = 'md',
  footer,
  showClose = true,
  closeOnOverlay = true,
  closeOnEscape = true,
  initialFocusRef,
  className,
  children,
}) {
  const dialogRef = useRef(null)
  const restoreFocusRef = useRef(null)
  const id = useId()
  const titleId = title ? `${id}-title` : undefined
  const descId = description ? `${id}-desc` : undefined

  const handleClose = useCallback(() => onClose?.(), [onClose])

  // The focus effect below must run on open/close and at no other time. Callers
  // routinely pass an inline `onClose`, which changes identity every render; if
  // the effect depended on it, each parent re-render would tear the trap down
  // (throwing focus back to the trigger) and rebuild it (grabbing the first
  // control), making it impossible to type in a modal form. Latest values are
  // read through a ref instead so the dependency list can stay [open].
  const latest = useRef({ handleClose, closeOnEscape, initialFocusRef })
  latest.current = { handleClose, closeOnEscape, initialFocusRef }

  // Lock the page behind the scrim, compensating for the scrollbar so the
  // layout underneath doesn't visibly jump when it disappears.
  useEffect(() => {
    if (!open) return
    const { body } = document
    const previousOverflow = body.style.overflow
    const previousPadding = body.style.paddingRight
    const gap = window.innerWidth - document.documentElement.clientWidth

    body.style.overflow = 'hidden'
    if (gap > 0) body.style.paddingRight = `${gap}px`

    return () => {
      body.style.overflow = previousOverflow
      body.style.paddingRight = previousPadding
    }
  }, [open])

  useEffect(() => {
    if (!open) return

    restoreFocusRef.current = document.activeElement

    const focusTarget =
      latest.current.initialFocusRef?.current ??
      dialogRef.current?.querySelector(FOCUSABLE) ??
      dialogRef.current
    focusTarget?.focus?.()

    const onKeyDown = (event) => {
      if (event.key === 'Escape' && latest.current.closeOnEscape) {
        event.stopPropagation()
        latest.current.handleClose()
        return
      }

      if (event.key !== 'Tab') return

      const nodes = Array.from(dialogRef.current?.querySelectorAll(FOCUSABLE) ?? []).filter(
        (n) => n.offsetParent !== null || n === document.activeElement,
      )
      if (nodes.length === 0) return

      const first = nodes[0]
      const last = nodes[nodes.length - 1]

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.removeEventListener('keydown', onKeyDown, true)
      restoreFocusRef.current?.focus?.()
    }
  }, [open])

  if (!open) return null

  return createPortal(
    <div
      className="ds ds-modal-overlay"
      onMouseDown={(event) => {
        // mousedown, not click: a drag that starts inside and ends on the
        // scrim must not be read as a dismissal.
        if (closeOnOverlay && event.target === event.currentTarget) handleClose()
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        tabIndex={-1}
        className={clsx('ds-modal', size !== 'md' && `ds-modal--${size}`, className)}
      >
        {title || showClose ? (
          <div className="ds-modal__header">
            <div className="ds-modal__heading">
              {eyebrow ? <span className="ds-modal__eyebrow">{eyebrow}</span> : null}
              {title ? (
                <h2 className="ds-modal__title" id={titleId}>
                  {title}
                </h2>
              ) : null}
              {description ? (
                <p className="ds-modal__desc" id={descId}>
                  {description}
                </p>
              ) : null}
            </div>
            {showClose ? <IconButton icon={X} label="Close dialog" onClick={handleClose} /> : null}
          </div>
        ) : null}

        <div className="ds-modal__body">{children}</div>

        {footer ? <div className="ds-modal__footer">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  )
}

/**
 * ConfirmDialog — the gate in front of anything irreversible.
 *
 * Cancel is listed first and the destructive action last and visually
 * separated, so the dangerous button is never where muscle memory expects OK.
 */
export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Confirm action',
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = true,
  loading = false,
  children,
}) {
  const cancelRef = useRef(null)

  return (
    <Modal
      open={open}
      onClose={loading ? () => {} : onClose}
      size="sm"
      showClose={false}
      closeOnOverlay={!loading}
      closeOnEscape={!loading}
      initialFocusRef={cancelRef}
      title={title}
      footer={
        <>
          <Button ref={cancelRef} variant="outline" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={destructive ? 'danger' : 'accent'}
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="ds-confirm__row">
        {destructive ? (
          <span className="ds-confirm__icon">
            <AlertTriangle size={18} strokeWidth={1.75} aria-hidden="true" />
          </span>
        ) : null}
        <div className="ds-stack ds-stack--2">
          {description ? <p className="ds-modal__desc">{description}</p> : null}
          {children}
        </div>
      </div>
    </Modal>
  )
}

export default Modal
