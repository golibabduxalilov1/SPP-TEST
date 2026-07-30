import { Fragment } from 'react'
import clsx from 'clsx'

/**
 * PageHeader — eyebrow, display title, description, actions, meta row.
 *
 * Only one action should carry a filled variant; everything else is outline or
 * quiet, so a page never presents two competing primary CTAs.
 */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  meta,
  breadcrumbs,
  className,
  children,
  ...rest
}) {
  return (
    <header className={clsx('ds-page-header', className)} {...rest}>
      {breadcrumbs ? <Breadcrumbs items={breadcrumbs} /> : null}

      <div className="ds-page-header__top">
        <div className="ds-page-header__heading">
          {eyebrow ? <span className="ds-page-header__eyebrow">{eyebrow}</span> : null}
          {title ? <h1 className="ds-page-header__title">{title}</h1> : null}
          {description ? <p className="ds-page-header__desc">{description}</p> : null}
        </div>

        {actions ? <div className="ds-page-header__actions">{actions}</div> : null}
      </div>

      {meta?.length ? (
        <div className="ds-page-header__meta">
          {meta.map((item) => (
            <div className="ds-page-header__meta-item" key={item.label}>
              <span className="ds-label">{item.label}</span>
              <span className="ds-page-header__meta-value">{item.value}</span>
            </div>
          ))}
        </div>
      ) : null}

      {children}
    </header>
  )
}

/** Orientation for 3+ level hierarchies. The last crumb is the current page. */
export function Breadcrumbs({ items = [], className, ...rest }) {
  return (
    <nav className={clsx('ds-breadcrumbs', className)} aria-label="Breadcrumb" {...rest}>
      {items.map((item, index) => {
        const last = index === items.length - 1
        return (
          <Fragment key={item.label}>
            {index > 0 ? (
              <span className="ds-breadcrumbs__sep" aria-hidden="true">
                /
              </span>
            ) : null}
            {last || !item.href ? (
              <span aria-current={last ? 'page' : undefined}>{item.label}</span>
            ) : (
              <a href={item.href}>{item.label}</a>
            )}
          </Fragment>
        )
      })}
    </nav>
  )
}

/**
 * SectionHeader — a rule-underlined divider between blocks of a page.
 * `index` takes the micro mono treatment ("01 / OVERVIEW").
 */
export function SectionHeader({
  index,
  title,
  description,
  actions,
  plain = false,
  className,
  as: Tag = 'h2',
  ...rest
}) {
  return (
    <div className={clsx('ds-section-header', plain && 'ds-section-header--plain', className)} {...rest}>
      <div className="ds-section-header__heading">
        {index ? <span className="ds-section-header__index">{index}</span> : null}
        {title ? <Tag className="ds-section-header__title">{title}</Tag> : null}
        {description ? <p className="ds-section-header__desc">{description}</p> : null}
      </div>
      {actions ? <div className="ds-section-header__actions">{actions}</div> : null}
    </div>
  )
}

export default PageHeader
