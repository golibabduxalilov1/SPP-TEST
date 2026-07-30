import { forwardRef } from 'react'
import clsx from 'clsx'
import { ChevronDown } from 'lucide-react'

/**
 * Select — a native <select> skinned to match Input exactly.
 *
 * Native is deliberate: it gives the platform picker on mobile, real keyboard
 * behaviour, and correct screen-reader semantics for free. Only the chevron is
 * custom, and it stays pointer-events:none so clicks fall through to the
 * control underneath.
 */
export const Select = forwardRef(function Select(
  { options = [], placeholder, value, className, children, ...rest },
  ref,
) {
  const showingPlaceholder = placeholder != null && (value === '' || value == null)

  return (
    <span className="ds-select">
      <select
        ref={ref}
        className={clsx('ds-select__control', className)}
        value={value}
        data-placeholder={showingPlaceholder || undefined}
        {...rest}
      >
        {placeholder != null ? (
          <option value="" disabled>
            {placeholder}
          </option>
        ) : null}

        {children ??
          options.map((opt) => {
            const o = typeof opt === 'object' ? opt : { value: opt, label: String(opt) }
            return (
              <option key={o.value} value={o.value} disabled={o.disabled}>
                {o.label}
              </option>
            )
          })}
      </select>

      <span className="ds-select__chevron" aria-hidden="true">
        <ChevronDown size={16} strokeWidth={1.75} />
      </span>
    </span>
  )
})

export default Select
