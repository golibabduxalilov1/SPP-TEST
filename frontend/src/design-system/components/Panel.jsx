import { forwardRef } from 'react'
import clsx from 'clsx'
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'

/**
 * Panel — a flat bordered surface. Shadow appears only on hover, and only when
 * `interactive` is set, so a static card never advertises a click that isn't
 * there. Rendering as a <button> when interactive keeps it keyboard-reachable.
 */
export const Panel = forwardRef(function Panel(
  { as, interactive = false, accent = false, sunken = false, flush = false, className, children, ...rest },
  ref,
) {
  const Tag = as ?? (interactive ? 'button' : 'div')

  return (
    <Tag
      ref={ref}
      type={Tag === 'button' ? 'button' : undefined}
      className={clsx(
        'ds-panel',
        interactive && 'ds-panel--interactive',
        accent && 'ds-panel--accent',
        sunken && 'ds-panel--sunken',
        flush && 'ds-panel--flush',
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  )
})

export function PanelHeader({ title, subtitle, actions, className, children, ...rest }) {
  return (
    <div className={clsx('ds-panel__header', className)} {...rest}>
      {children ?? (
        <div>
          {title ? <h3 className="ds-panel__title">{title}</h3> : null}
          {subtitle ? <p className="ds-panel__subtitle">{subtitle}</p> : null}
        </div>
      )}
      {actions ? <div className="ds-panel__actions">{actions}</div> : null}
    </div>
  )
}

export function PanelBody({ flush = false, className, children, ...rest }) {
  return (
    <div className={clsx('ds-panel__body', flush && 'ds-panel__body--flush', className)} {...rest}>
      {children}
    </div>
  )
}

export function PanelFooter({ className, children, ...rest }) {
  return (
    <div className={clsx('ds-panel__footer', className)} {...rest}>
      {children}
    </div>
  )
}

const DELTA_ICON = { up: ArrowUpRight, down: ArrowDownRight, flat: Minus }

/**
 * Stat — a mono figure over a mono label, for KPI rows.
 *
 * The delta pairs an arrow with the colour so direction is still readable
 * without colour perception.
 */
export function Stat({ label, value, delta, direction = 'flat', caption, className, ...rest }) {
  const DeltaIcon = DELTA_ICON[direction] ?? Minus

  return (
    <div className={clsx('ds-stat', className)} {...rest}>
      {label ? <span className="ds-label">{label}</span> : null}
      <span className="ds-stat__value">{value}</span>
      {delta != null ? (
        <span className={`ds-stat__delta ds-stat__delta--${direction}`}>
          <DeltaIcon size={12} strokeWidth={2.25} aria-hidden="true" />
          {delta}
        </span>
      ) : null}
      {caption ? <span className="ds-field__hint">{caption}</span> : null}
    </div>
  )
}

export default Panel
