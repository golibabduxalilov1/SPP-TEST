import { useMemo, useState } from 'react'
import clsx from 'clsx'
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react'
import { Skeleton } from './Skeleton.jsx'
import { EmptyState } from './EmptyState.jsx'

/**
 * DataTable — thin-ruled, mono-headed, horizontally scrollable.
 *
 * Columns:
 *   { key, header, align: 'left'|'right', numeric, primary, sortable,
 *     width, render(row, index), sortValue(row) }
 *
 * Sorting is uncontrolled by default and becomes controlled the moment `sort`
 * and `onSortChange` are both supplied — so a server-paginated table can own
 * ordering while a small client-side table needs no wiring at all.
 *
 * The three body states (loading / empty / rows) are mutually exclusive and all
 * render inside the same bordered frame, so the layout never jumps between them.
 */
export function DataTable({
  columns = [],
  rows = [],
  getRowId,
  loading = false,
  skeletonRows = 5,
  emptyTitle = 'No records',
  emptyDescription,
  emptyAction,
  caption,
  sort: controlledSort,
  onSortChange,
  onRowClick,
  isRowSelected,
  footer,
  className,
  ...rest
}) {
  const [internalSort, setInternalSort] = useState(null)
  const isControlled = controlledSort !== undefined && typeof onSortChange === 'function'
  const sort = isControlled ? controlledSort : internalSort

  const setSort = (next) => {
    if (isControlled) onSortChange(next)
    else setInternalSort(next)
  }

  const toggleSort = (key) => {
    if (sort?.key === key) {
      // asc → desc → unsorted, so a user can always get back to source order.
      setSort(sort.direction === 'asc' ? { key, direction: 'desc' } : null)
    } else {
      setSort({ key, direction: 'asc' })
    }
  }

  const sortedRows = useMemo(() => {
    // Controlled mode means the caller already ordered the data.
    if (!sort || isControlled) return rows

    const column = columns.find((c) => c.key === sort.key)
    if (!column) return rows

    const read = column.sortValue ?? ((row) => row[column.key])
    const factor = sort.direction === 'asc' ? 1 : -1

    return [...rows].sort((a, b) => {
      const av = read(a)
      const bv = read(b)
      if (av == null && bv == null) return 0
      if (av == null) return 1 * factor
      if (bv == null) return -1 * factor
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * factor
      return String(av).localeCompare(String(bv), undefined, { numeric: true }) * factor
    })
  }, [rows, sort, columns, isControlled])

  const colCount = columns.length || 1

  return (
    <div className={clsx('ds-table-wrap', className)} {...rest}>
      <table
        className={clsx('ds-table', onRowClick && 'ds-table--rows-clickable')}
        aria-busy={loading || undefined}
      >
        {caption ? <caption>{caption}</caption> : null}

        <thead>
          <tr>
            {columns.map((col) => {
              const active = sort?.key === col.key
              const ariaSort = active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'
              const SortIcon = active ? (sort.direction === 'asc' ? ChevronUp : ChevronDown) : ChevronsUpDown

              return (
                <th
                  key={col.key}
                  scope="col"
                  style={col.width ? { width: col.width } : undefined}
                  aria-sort={col.sortable ? ariaSort : undefined}
                  className={clsx(
                    col.numeric && 'ds-table__cell--numeric',
                    col.index && 'ds-table__cell--index',
                    col.align === 'right' && 'ds-table__cell--numeric',
                    col.actions && 'ds-table__cell--actions',
                  )}
                >
                  {col.sortable ? (
                    <button
                      type="button"
                      className="ds-table__sort"
                      data-active={active || undefined}
                      onClick={() => toggleSort(col.key)}
                    >
                      {col.header}
                      <SortIcon className="ds-table__sort-icon" size={12} strokeWidth={2} aria-hidden="true" />
                      <span className="ds-sr-only">
                        {active
                          ? `sorted ${sort.direction === 'asc' ? 'ascending' : 'descending'}, activate to change`
                          : 'activate to sort'}
                      </span>
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              )
            })}
          </tr>
        </thead>

        <tbody>
          {loading ? (
            Array.from({ length: skeletonRows }, (_, r) => (
              <tr key={`skeleton-${r}`}>
                {columns.map((col) => (
                  <td key={col.key}>
                    <Skeleton variant="text" width={col.numeric ? '56px' : '72%'} />
                  </td>
                ))}
              </tr>
            ))
          ) : sortedRows.length === 0 ? (
            <tr className="ds-table__message">
              <td colSpan={colCount}>
                <EmptyState
                  compact
                  title={emptyTitle}
                  description={emptyDescription}
                  action={emptyAction}
                />
              </td>
            </tr>
          ) : (
            sortedRows.map((row, index) => {
              const id = getRowId ? getRowId(row, index) : (row.id ?? index)
              return (
                <tr
                  key={id}
                  data-selected={isRowSelected?.(row) || undefined}
                  onClick={onRowClick ? () => onRowClick(row, index) : undefined}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={clsx(
                        col.primary && 'ds-table__cell--primary',
                        col.numeric && 'ds-table__cell--numeric',
                        col.index && 'ds-table__cell--index',
                        col.align === 'right' && 'ds-table__cell--numeric',
                        col.actions && 'ds-table__cell--actions',
                      )}
                    >
                      {col.render ? col.render(row, index) : row[col.key]}
                    </td>
                  ))}
                </tr>
              )
            })
          )}
        </tbody>

        {footer && !loading && sortedRows.length > 0 ? (
          <tfoot className="ds-table__foot">{footer}</tfoot>
        ) : null}
      </table>
    </div>
  )
}

export default DataTable
