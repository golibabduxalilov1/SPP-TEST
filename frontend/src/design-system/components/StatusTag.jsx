import clsx from 'clsx'

/**
 * StatusTag — compact, almost-square, 11px mono.
 *
 * Semantic colour carries status only, never decoration. The text label is
 * always rendered and an optional square dot or icon backs it up, so the
 * meaning survives without colour perception.
 */
export function StatusTag({
  variant = 'neutral',
  dot = false,
  icon: Icon,
  solid = false,
  className,
  children,
  ...rest
}) {
  return (
    <span
      className={clsx('ds-tag', `ds-tag--${variant}`, solid && 'ds-tag--solid', className)}
      {...rest}
    >
      {dot ? <span className="ds-tag__dot" aria-hidden="true" /> : null}
      {Icon ? <Icon size={11} strokeWidth={2.25} aria-hidden="true" /> : null}
      {children}
    </span>
  )
}

export default StatusTag
