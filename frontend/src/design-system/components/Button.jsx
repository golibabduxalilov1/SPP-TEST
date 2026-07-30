import { forwardRef } from 'react'
import clsx from 'clsx'

/**
 * Button — solid / accent / outline / quiet / danger.
 *
 * Never shrinks below the 44px touch floor and never animates a transform, so
 * pressing one can't shift the layout around it. While `loading` is true the
 * label keeps its box (visibility, not display) and the button stops
 * responding, so an async submit can't be fired twice.
 */
export const Button = forwardRef(function Button(
  {
    as: Tag = 'button',
    variant = 'outline',
    size = 'md',
    block = false,
    loading = false,
    disabled = false,
    icon: Icon,
    iconAfter: IconAfter,
    iconSize = 16,
    className,
    children,
    type,
    onClick,
    ...rest
  },
  ref,
) {
  const inert = disabled || loading
  const isButton = Tag === 'button'

  return (
    <Tag
      ref={ref}
      type={isButton ? (type ?? 'button') : type}
      className={clsx(
        'ds-btn',
        `ds-btn--${variant}`,
        size === 'cta' && 'ds-btn--cta',
        size === 'sm' && 'ds-btn--sm',
        block && 'ds-btn--block',
        className,
      )}
      // Non-button elements can't carry `disabled`; aria-disabled keeps them
      // announced correctly and the click guard below makes it real.
      disabled={isButton ? inert : undefined}
      aria-disabled={!isButton && inert ? true : undefined}
      aria-busy={loading || undefined}
      onClick={inert ? (e) => e.preventDefault() : onClick}
      {...rest}
    >
      <span className="ds-btn__label">
        {Icon ? <Icon size={iconSize} strokeWidth={1.75} className="ds-btn__icon" aria-hidden="true" /> : null}
        {children}
        {IconAfter ? <IconAfter size={iconSize} strokeWidth={1.75} className="ds-btn__icon" aria-hidden="true" /> : null}
      </span>

      {loading ? (
        <span className="ds-btn__spinner">
          <span className="ds-spinner" />
          <span className="ds-sr-only">Loading</span>
        </span>
      ) : null}
    </Tag>
  )
})

/**
 * IconButton — exactly 44×44. `label` is required and becomes the accessible
 * name plus the native tooltip, because an icon alone names nothing.
 */
export const IconButton = forwardRef(function IconButton(
  { icon: Icon, label, variant = 'quiet', size = 'md', loading = false, disabled = false, iconSize = 18, className, ...rest },
  ref,
) {
  return (
    <Button
      ref={ref}
      variant={variant}
      size={size}
      loading={loading}
      disabled={disabled}
      className={clsx('ds-btn--icon', className)}
      aria-label={label}
      title={label}
      {...rest}
    >
      {Icon ? <Icon size={iconSize} strokeWidth={1.75} aria-hidden="true" /> : null}
    </Button>
  )
})

export default Button
