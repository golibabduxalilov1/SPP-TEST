import { forwardRef, useId } from 'react'
import clsx from 'clsx'
import { AlertCircle } from 'lucide-react'

/**
 * Field — the label / control / hint / error wrapper every form control shares.
 *
 * Renders as a render-prop so the control receives the wiring it needs
 * (`id`, `aria-describedby`, `aria-invalid`) without the caller repeating it.
 * The hint stays mounted while an error shows so the box height is stable and
 * the error never pushes the next field down.
 */
export function Field({
  label,
  hint,
  error,
  required = false,
  optional = false,
  disabled = false,
  loading = false,
  htmlFor,
  className,
  children,
  ...rest
}) {
  const autoId = useId()
  const id = htmlFor ?? autoId
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [errorId, hintId].filter(Boolean).join(' ') || undefined

  const control =
    typeof children === 'function'
      ? children({
          id,
          disabled,
          'aria-describedby': describedBy,
          'aria-invalid': error ? true : undefined,
          'aria-errormessage': errorId,
          'aria-required': required || undefined,
        })
      : children

  return (
    <div
      className={clsx(
        'ds-field',
        error && 'ds-field--invalid',
        loading && 'ds-field--loading',
        className,
      )}
      {...rest}
    >
      {label ? (
        <label className="ds-field__label" htmlFor={id}>
          {label}
          {required ? (
            <span className="ds-field__required" aria-hidden="true">
              *
            </span>
          ) : null}
          {optional && !required ? <span className="ds-field__optional">optional</span> : null}
        </label>
      ) : null}

      <div className="ds-field__control">{control}</div>

      {/* role="alert" so a screen reader announces validation without a focus jump. */}
      {error ? (
        <p className="ds-field__error" id={errorId} role="alert">
          <AlertCircle size={13} strokeWidth={2} aria-hidden="true" />
          <span>{error}</span>
        </p>
      ) : null}

      {hint ? (
        <p className="ds-field__hint" id={hintId}>
          {hint}
        </p>
      ) : null}
    </div>
  )
}

export const Input = forwardRef(function Input(
  { numeric = false, leading: Leading, trailing, className, ...rest },
  ref,
) {
  return (
    <>
      {Leading ? (
        <span className="ds-field__affix ds-field__affix--leading" aria-hidden="true">
          <Leading size={16} strokeWidth={1.75} />
        </span>
      ) : null}

      <input
        ref={ref}
        className={clsx(
          'ds-input',
          numeric && 'ds-input--numeric',
          Leading && 'ds-input--has-leading',
          trailing && 'ds-input--has-trailing',
          className,
        )}
        {...rest}
      />

      {trailing ? (
        <span className="ds-field__affix ds-field__affix--trailing ds-field__affix--action">
          {trailing}
        </span>
      ) : null}
    </>
  )
})

export const Textarea = forwardRef(function Textarea({ rows = 4, className, ...rest }, ref) {
  return <textarea ref={ref} rows={rows} className={clsx('ds-textarea', className)} {...rest} />
})

export default Field
