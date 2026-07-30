import clsx from 'clsx'
import { Inbox } from 'lucide-react'

/**
 * EmptyState — "nothing here" plus the way out.
 *
 * An empty region always needs a reason and a next step; a blank panel reads
 * as a bug. `variant="error"` reuses the same shell for load failures, where
 * the action becomes a retry.
 */
export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  compact = false,
  variant = 'default',
  className,
  children,
  ...rest
}) {
  return (
    <div
      className={clsx(
        'ds-empty',
        compact && 'ds-empty--compact',
        variant === 'error' && 'ds-empty--error',
        className,
      )}
      {...rest}
    >
      {Icon ? (
        <span className="ds-empty__icon">
          <Icon size={20} strokeWidth={1.5} aria-hidden="true" />
        </span>
      ) : null}

      {title ? <p className="ds-empty__title">{title}</p> : null}
      {description ? <p className="ds-empty__desc">{description}</p> : null}
      {children}
      {action ? <div className="ds-empty__actions">{action}</div> : null}
    </div>
  )
}

export default EmptyState
