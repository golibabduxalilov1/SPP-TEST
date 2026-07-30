import clsx from 'clsx'

/**
 * Skeleton — a shimmering placeholder that reserves the real element's box.
 *
 * Always give it the dimensions the loaded content will occupy; that's the
 * whole point, and it's what keeps cumulative layout shift at zero. The
 * shimmer animation is dropped entirely under prefers-reduced-motion (see
 * components.css).
 */
export function Skeleton({ variant = 'text', width, height, className, style, ...rest }) {
  return (
    <span
      className={clsx('ds-skeleton', `ds-skeleton--${variant}`, className)}
      style={{ width, height, ...style }}
      aria-hidden="true"
      {...rest}
    />
  )
}

/** A block of stacked text lines, last one short like real prose. */
export function SkeletonText({ lines = 3, className, ...rest }) {
  return (
    <span className={clsx('ds-stack ds-stack--2', className)} {...rest}>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} variant="text" width={i === lines - 1 ? '58%' : '100%'} />
      ))}
    </span>
  )
}

/**
 * Wraps a loading region so screen readers are told work is in progress —
 * the visual shimmer alone announces nothing.
 */
export function SkeletonRegion({ loading, label = 'Loading', children, ...rest }) {
  return (
    <div aria-busy={loading || undefined} aria-live="polite" {...rest}>
      {loading ? <span className="ds-sr-only">{label}</span> : null}
      {children}
    </div>
  )
}

export default Skeleton
