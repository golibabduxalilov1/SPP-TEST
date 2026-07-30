# Swiss Modernism 2.0 — Design System

A self-contained set of visual tokens and React primitives. Precise, calm,
high-contrast, data-friendly.

## Isolation guarantee

**This system does not change the host application's colours.** Every token and
every rule is scoped to the `.ds` root class that `<ResponsiveShell>` applies.
Nothing is registered on `:root`, `body`, or any bare element selector.

Concretely:

- `src/index.css` and `src/design/tokens.css` are **not** modified or imported.
- The app's existing palette keeps its own `--canvas`, `--ink`, etc. Ours are
  all `--ds-*`, so the two namespaces cannot collide.
- CSS loads only when something imports the design system. If nothing does, the
  bundle is unchanged.

This project defines no path alias, so import it relatively —
`../design-system` from `src/pages/`, `../../design-system` one level deeper.

Do **not** add `tokens.css` or `components.css` to `src/index.css` — that would
break the isolation.

## Usage

```jsx
import { ResponsiveShell, ShellMain, Container, Button, ToastProvider } from '../design-system'

export default function Page() {
  return (
    <ToastProvider>
      <ResponsiveShell>
        <ShellMain>
          <Container>
            <Button variant="accent">Continue</Button>
          </Container>
        </ShellMain>
      </ResponsiveShell>
    </ToastProvider>
  )
}
```

Everything must live inside a `.ds` root. `<ResponsiveShell>` supplies it;
`<Modal>` and `<ToastProvider>` add it to their own portal nodes automatically.

## Tokens

Read from `--ds-*` variables; never hard-code a hex value downstream.

| Group | Tokens |
|---|---|
| Surfaces | `--ds-canvas` `--ds-panel` `--ds-sunken` `--ds-veil` |
| Ink | `--ds-text` `--ds-text-secondary` `--ds-text-muted` |
| Lines | `--ds-border` `--ds-border-strong` |
| Dark | `--ds-dark` `--ds-dark-hover` `--ds-on-dark` `--ds-on-dark-muted` |
| Accent | `--ds-accent` `--ds-accent-hover` `--ds-accent-dark` `--ds-accent-tint` |
| Status | `--ds-success` `--ds-warning` `--ds-error` `--ds-info` (+ `-tint`) |
| Spacing | `--ds-space-1` … `--ds-space-24`, strictly 4px multiples |
| Radii | `--ds-radius-tag` 2px · `--ds-radius-control` 4px · `--ds-radius-panel` 6px |
| Motion | `--ds-duration-fast` 150ms · `-base` 200ms · `-slow` 300ms · `--ds-ease` |

Typography: **Space Grotesk** display, **Inter** body/UI, **JetBrains Mono**
labels, figures, table headers, status, metadata. Use `.ds-numeric` or a
`numeric` prop wherever numbers are compared column-wise.

## Layout

`<Band>` (full-bleed) → `<Container>` (1200px, 20/32/40px gutters) →
`<Grid>` / `<Col md lg>` (12 columns, single column below 768px) →
`<Stack gap>` / `<Cluster>`.

`tone="dark"` on a `<Band>` is reserved for hero and footer only.

## Components

| Component | Notes |
|---|---|
| `Button` | `solid` `accent` `outline` `quiet` `danger` `danger-outline`; sizes `sm` `md` `cta`; `loading` keeps the label's box so the button never resizes |
| `IconButton` | Exactly 44×44. `label` is required and becomes the accessible name |
| `Field` | Render-prop wrapper wiring `id` / `aria-describedby` / `aria-invalid`; states: required, optional, hint, error, disabled, loading |
| `Input` `Textarea` | 44px floor, 15px Inter, indigo focus ring; textarea resizes vertically only |
| `Select` | Native `<select>` skinned to match `Input` — real platform picker and keyboard behaviour |
| `Checkbox` | 20×20 box, 2px radius, indigo when checked; supports `indeterminate` |
| `Panel` | Flat by default; shadow only on hover and only when `interactive` |
| `Stat` | Mono figure + delta arrow, so direction reads without colour |
| `StatusTag` | `neutral` `accent` `positive` `caution` `critical` `informative` |
| `DataTable` | Overflow container, sticky mono header, `aria-sort`; loading and empty states share the frame so nothing jumps |
| `Skeleton` | Shimmer; give it the loaded element's real dimensions to keep CLS at zero |
| `EmptyState` | `variant="error"` reuses the shell for load failures |
| `Modal` | Portal, focus trap, Escape, scroll lock, focus restored on close; bottom sheet under 640px |
| `ConfirmDialog` | Cancel focused first, destructive action last and separated |
| `ToastProvider` / `useToast` | `aria-live="polite"`, never steals focus, timers pause on hover and focus |
| `PageHeader` `SectionHeader` `Breadcrumbs` | One filled action per page — everything else outline or quiet |

## Accessibility

- One focus-visible treatment: 2px indigo, 2px offset. Form controls use the
  3px ring instead.
- 44px minimum on every interactive control.
- Colour is never the only signal: errors pair red with an icon, status tags
  always carry text, stat deltas carry an arrow.
- `prefers-reduced-motion` disables animation everywhere inside `.ds`.
- Motion is limited to 150 / 200 / 300ms on `cubic-bezier(0.2, 0, 0, 1)`; no
  scale or bounce on hover, and nothing that shifts layout.
