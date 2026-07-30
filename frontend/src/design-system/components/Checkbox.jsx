import { forwardRef, useEffect, useId, useRef } from 'react'
import clsx from 'clsx'
import { Check, Minus } from 'lucide-react'

/**
 * Checkbox — 20×20 box, 2px radius, indigo when selected.
 *
 * The visible box stays 20px while the surrounding <label> carries vertical
 * padding up to the 44px touch floor, so the target is finger-sized without
 * the control looking oversized.
 *
 * `indeterminate` is a DOM property, not an attribute, so it has to be set
 * imperatively — React won't do it from JSX.
 */
export const Checkbox = forwardRef(function Checkbox(
  { label, description, indeterminate = false, disabled = false, className, id, ...rest },
  ref,
) {
  const innerRef = useRef(null)
  const autoId = useId()
  const inputId = id ?? autoId
  const descId = description ? `${inputId}-desc` : undefined

  useEffect(() => {
    const node = innerRef.current
    if (node) node.indeterminate = indeterminate
  }, [indeterminate])

  const setRefs = (node) => {
    innerRef.current = node
    if (typeof ref === 'function') ref(node)
    else if (ref) ref.current = node
  }

  const Mark = indeterminate ? Minus : Check

  return (
    <label
      htmlFor={inputId}
      className={clsx('ds-checkbox', disabled && 'ds-checkbox--disabled', className)}
    >
      <span className="ds-checkbox__box">
        <input
          ref={setRefs}
          id={inputId}
          type="checkbox"
          className="ds-checkbox__input"
          disabled={disabled}
          aria-describedby={descId}
          {...rest}
        />
        <Mark className="ds-checkbox__mark" size={13} strokeWidth={3} aria-hidden="true" />
      </span>

      {label || description ? (
        <span className="ds-checkbox__text">
          {label}
          {description ? (
            <span className="ds-checkbox__desc" id={descId}>
              {description}
            </span>
          ) : null}
        </span>
      ) : null}
    </label>
  )
})

export default Checkbox
