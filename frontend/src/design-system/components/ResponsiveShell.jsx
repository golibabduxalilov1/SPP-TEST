import clsx from 'clsx'

/**
 * ResponsiveShell — the mount point for the whole system.
 *
 * The `ds` class is what every token in tokens.css is scoped to, so nothing
 * inside this system applies until an ancestor carries it. That's deliberate:
 * it lets the design system sit inside an app that has its own theme without
 * either one leaking into the other.
 */
export function ResponsiveShell({ as: Tag = 'div', className, children, ...rest }) {
  return (
    <Tag className={clsx('ds ds-shell', className)} {...rest}>
      {children}
    </Tag>
  )
}

/** The scrollable page body. Wrap page content so a sticky header can't cover it. */
export function ShellMain({ as: Tag = 'main', className, children, ...rest }) {
  return (
    <Tag className={clsx('ds-shell__main', className)} {...rest}>
      {children}
    </Tag>
  )
}

/** 1200px measure with 20 / 32 / 40px gutters. Everything aligns to this. */
export function Container({ as: Tag = 'div', wide = false, flush = false, className, children, ...rest }) {
  return (
    <Tag
      className={clsx('ds-container', wide && 'ds-container--wide', flush && 'ds-container--flush', className)}
      {...rest}
    >
      {children}
    </Tag>
  )
}

/**
 * Band — a full-bleed horizontal surface.
 *
 * `tone="dark"` is reserved for hero and footer; using it mid-page turns the
 * layout into stripes and costs the interface its calm.
 */
export function Band({ as: Tag = 'section', tone = 'default', size = 'md', inner = true, className, children, ...rest }) {
  return (
    <Tag
      className={clsx('ds-band', tone === 'dark' && 'ds-band--dark', tone === 'sunken' && 'ds-band--sunken', className)}
      {...rest}
    >
      {inner ? (
        <div className={clsx('ds-band__inner', size !== 'md' && `ds-band__inner--${size}`)}>
          <Container>{children}</Container>
        </div>
      ) : (
        children
      )}
    </Tag>
  )
}

/** 12-column grid. Collapses to a single column below 768px, always. */
export function Grid({ as: Tag = 'div', gap, className, children, ...rest }) {
  return (
    <Tag
      className={clsx('ds-grid', className)}
      style={gap ? { '--ds-grid-gap': gap } : undefined}
      {...rest}
    >
      {children}
    </Tag>
  )
}

/** A grid cell. `md` / `lg` are column spans out of 12 at each breakpoint. */
export function Col({ as: Tag = 'div', md, lg, className, children, ...rest }) {
  return (
    <Tag
      className={clsx('ds-col', md && `ds-col--md-${md}`, lg && `ds-col--lg-${lg}`, className)}
      {...rest}
    >
      {children}
    </Tag>
  )
}

/** Vertical spacing off the 4px scale — 1, 2, 3, 4, 6, 8, 12. */
export function Stack({ as: Tag = 'div', gap = 4, className, children, ...rest }) {
  return (
    <Tag className={clsx('ds-stack', `ds-stack--${gap}`, className)} {...rest}>
      {children}
    </Tag>
  )
}

/** Horizontal group that wraps — toolbars, tag rows, button pairs. */
export function Cluster({ as: Tag = 'div', gap, className, children, ...rest }) {
  return (
    <Tag
      className={clsx('ds-cluster', className)}
      style={gap ? { '--ds-cluster-gap': gap } : undefined}
      {...rest}
    >
      {children}
    </Tag>
  )
}

export function Rule({ strong = false, className, ...rest }) {
  return <hr className={clsx('ds-rule', strong && 'ds-rule-strong', className)} {...rest} />
}

export function Toolbar({ className, children, ...rest }) {
  return (
    <div className={clsx('ds-toolbar', className)} {...rest}>
      {children}
    </div>
  )
}

export function ToolbarSpacer() {
  return <span className="ds-toolbar__spacer" />
}

export function Divider() {
  return <span className="ds-divider" aria-hidden="true" />
}

export default ResponsiveShell
