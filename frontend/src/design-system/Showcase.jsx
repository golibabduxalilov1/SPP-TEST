import { useState } from 'react'
import {
  ArrowRight,
  Check,
  Download,
  MoreHorizontal,
  Plus,
  Search,
  Trash2,
} from 'lucide-react'

import {
  Band,
  Breadcrumbs,
  Button,
  Checkbox,
  Col,
  Cluster,
  ConfirmDialog,
  Container,
  DataTable,
  Divider,
  EmptyState,
  Field,
  Grid,
  IconButton,
  Input,
  Modal,
  Panel,
  PanelBody,
  PanelFooter,
  PanelHeader,
  PageHeader,
  ResponsiveShell,
  Rule,
  SectionHeader,
  Select,
  ShellMain,
  Skeleton,
  Stack,
  Stat,
  StatusTag,
  Textarea,
  Toolbar,
  ToolbarSpacer,
  ToastProvider,
  useToast,
} from './index.js'

/* ============================================================================
   Showcase — the system's reference implementation.

   Every primitive appears here in each of its states, which makes this both the
   living documentation and the page to open when checking a change didn't break
   something three components away.

   The content is deliberately abstract. This file is a specimen sheet, not a
   template: nothing here is modelled on any real screen, and it is not routed
   into the application. Mount it behind a throwaway route when you want to look
   at it:

     import DesignSystemShowcase from '../design-system/Showcase.jsx'
     <Route path="/design-system" element={<DesignSystemShowcase />} />
   ============================================================================ */

const COLUMNS = [
  { key: 'index', header: '#', index: true },
  { key: 'name', header: 'Record', primary: true, sortable: true },
  {
    key: 'status',
    header: 'Status',
    render: (row) => (
      <StatusTag variant={row.tone} dot>
        {row.status}
      </StatusTag>
    ),
  },
  { key: 'channel', header: 'Channel', sortable: true },
  { key: 'units', header: 'Units', numeric: true, sortable: true },
  { key: 'value', header: 'Value', numeric: true, sortable: true, sortValue: (r) => r.valueRaw },
]

const ROWS = [
  { id: 1, index: '01', name: 'Alpha specimen', status: 'Active', tone: 'positive', channel: 'Direct', units: 1240, valueRaw: 18400, value: '18,400.00' },
  { id: 2, index: '02', name: 'Beta specimen', status: 'Pending', tone: 'caution', channel: 'Partner', units: 86, valueRaw: 2150, value: '2,150.00' },
  { id: 3, index: '03', name: 'Gamma specimen', status: 'Blocked', tone: 'critical', channel: 'Direct', units: 0, valueRaw: 0, value: '0.00' },
  { id: 4, index: '04', name: 'Delta specimen', status: 'Review', tone: 'informative', channel: 'Reseller', units: 512, valueRaw: 9075, value: '9,075.00' },
  { id: 5, index: '05', name: 'Epsilon specimen', status: 'Draft', tone: 'neutral', channel: 'Partner', units: 24, valueRaw: 640, value: '640.00' },
]

const TAGS = ['neutral', 'accent', 'positive', 'caution', 'critical', 'informative']

function Swatch({ token, name, dark = false }) {
  return (
    <Stack gap={2}>
      <span
        style={{
          height: 56,
          borderRadius: 'var(--ds-radius-control)',
          background: `var(${token})`,
          border: '1px solid var(--ds-border)',
        }}
      />
      <span className="ds-label">{name}</span>
      <span className="ds-mono" style={{ fontSize: 11, color: dark ? 'var(--ds-on-dark-muted)' : 'var(--ds-text-muted)' }}>
        {token}
      </span>
    </Stack>
  )
}

function ShowcaseBody() {
  const { toast, success, error } = useToast()

  const [modalOpen, setModalOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [tableLoading, setTableLoading] = useState(false)
  const [emptied, setEmptied] = useState(false)
  const [terms, setTerms] = useState(false)
  const [name, setName] = useState('')

  // Deliberately naive: the point is to show the error state, not to validate.
  const nameError = name.trim().length > 0 && name.trim().length < 3 ? 'Must be at least 3 characters.' : undefined

  return (
    <ResponsiveShell>
      {/* -- Hero: one of only two places a dark full-bleed surface is allowed -- */}
      <Band tone="dark" size="lg" as="header">
        <Stack gap={6}>
          <span className="ds-label-micro">Design system · v1</span>
          <h1 className="ds-display-1">
            Swiss Modernism 2.0
          </h1>
          <p className="ds-lede" style={{ maxWidth: '62ch', color: 'var(--ds-on-dark-muted)' }}>
            A specimen sheet for the tokens and primitives. Precise, calm, high-contrast,
            data-friendly — thin rules and whitespace instead of shadows, one accent colour,
            and a 4px grid underneath everything.
          </p>
          <Cluster gap="12px">
            <Button variant="accent" size="cta" iconAfter={ArrowRight}>
              Primary call to action
            </Button>
            <Button variant="outline" size="cta">
              Secondary
            </Button>
          </Cluster>
        </Stack>
      </Band>

      <ShellMain>
        <Container>
          <PageHeader
            breadcrumbs={[
              { label: 'System', href: '#' },
              { label: 'Foundations', href: '#' },
              { label: 'Specimen' },
            ]}
            eyebrow="Foundations"
            title="Primitives and states"
            description="Every component below is shown in each state it supports, including the ones that are easy to forget: loading, disabled, empty, error, and read-only."
            actions={
              <>
                <Button variant="quiet" icon={Download}>
                  Export
                </Button>
                <Button variant="accent" icon={Plus}>
                  New record
                </Button>
              </>
            }
            meta={[
              { label: 'Tokens', value: '96' },
              { label: 'Primitives', value: '16' },
              { label: 'Base unit', value: '4px' },
              { label: 'Measure', value: '1200px' },
            ]}
          />
        </Container>

        {/* ---- Colour ------------------------------------------------------ */}
        <Band tone="sunken">
          <SectionHeader
            index="01 / Colour"
            title="Palette"
            description="White and neutral zinc, with indigo as the only decorative colour. Semantic hues appear on status alone and never as decoration."
          />
          <Grid>
            <Col md={3} lg={2}><Swatch token="--ds-canvas" name="Canvas" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-sunken" name="Sunken" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-veil" name="Veil" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-border" name="Border" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-border-strong" name="Border strong" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-text" name="Ink" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-accent" name="Accent" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-accent-hover" name="Accent hover" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-accent-tint" name="Accent tint" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-success" name="Success" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-warning" name="Warning" /></Col>
            <Col md={3} lg={2}><Swatch token="--ds-error" name="Error" /></Col>
          </Grid>
        </Band>

        {/* ---- Typography -------------------------------------------------- */}
        <Band>
          <SectionHeader
            index="02 / Typography"
            title="Type scale"
            description="Space Grotesk for display, Inter for everything you read or operate, JetBrains Mono for labels, figures and metadata."
          />
          <Stack gap={6}>
            <Stack gap={2}>
              <span className="ds-label">Display 1 · Space Grotesk · −0.04em</span>
              <p className="ds-display-1">Grid, rule, measure</p>
            </Stack>
            <Rule />
            <Stack gap={2}>
              <span className="ds-label">Display 3</span>
              <p className="ds-display-3">Alignment does the decorating</p>
            </Stack>
            <Rule />
            <Stack gap={2}>
              <span className="ds-label">Body · Inter 15px</span>
              <p style={{ maxWidth: '68ch' }}>
                Body copy sits at 15px with a 1.5 line height and a measure capped near 68
                characters, which is where a line stops being comfortable to track back from.
                Secondary text drops to zinc-700; muted metadata to zinc-500.
              </p>
            </Stack>
            <Rule />
            <Stack gap={2}>
              <span className="ds-label">Numerals · JetBrains Mono · tabular</span>
              <p className="ds-numeric" style={{ fontSize: 24 }}>
                18,400.00 · 2,150.00 · 9,075.00 · 640.00
              </p>
            </Stack>
          </Stack>
        </Band>

        {/* ---- Buttons ----------------------------------------------------- */}
        <Band tone="sunken">
          <SectionHeader
            index="03 / Action"
            title="Buttons"
            description="44px floor on every variant, 4px radius, 150ms colour transitions. No scale, no bounce, nothing that shifts the layout around it."
          />
          <Stack gap={6}>
            <Stack gap={3}>
              <span className="ds-label">Variants</span>
              <Cluster gap="12px">
                <Button variant="solid">Solid</Button>
                <Button variant="accent">Accent</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="quiet">Quiet</Button>
                <Button variant="danger" icon={Trash2}>Destructive</Button>
                <Button variant="danger-outline">Destructive outline</Button>
              </Cluster>
            </Stack>

            <Stack gap={3}>
              <span className="ds-label">Sizes · 44px / 44px / 52px</span>
              <Cluster gap="12px">
                <Button variant="outline" size="sm">Small</Button>
                <Button variant="outline">Medium</Button>
                <Button variant="accent" size="cta">Large CTA</Button>
              </Cluster>
            </Stack>

            <Stack gap={3}>
              <span className="ds-label">States</span>
              <Cluster gap="12px">
                <Button variant="solid" loading>Loading</Button>
                <Button variant="accent" disabled>Disabled</Button>
                <Button variant="outline" disabled>Disabled outline</Button>
                <Button variant="outline" icon={Check}>With icon</Button>
                <Button variant="quiet" iconAfter={ArrowRight}>Trailing icon</Button>
              </Cluster>
            </Stack>

            <Stack gap={3}>
              <span className="ds-label">Icon-only · exactly 44×44</span>
              <Cluster gap="12px">
                <IconButton icon={Search} label="Search" />
                <IconButton icon={Plus} label="Add record" variant="outline" />
                <IconButton icon={Download} label="Download" variant="solid" />
                <IconButton icon={Trash2} label="Delete" variant="danger" />
                <IconButton icon={MoreHorizontal} label="More actions" disabled />
              </Cluster>
            </Stack>
          </Stack>
        </Band>

        {/* ---- Forms ------------------------------------------------------- */}
        <Band>
          <SectionHeader
            index="04 / Input"
            title="Forms"
            description="Labels are 11px uppercase mono and always visible. Errors sit beside the field they belong to, paired with an icon so red is never the only signal."
          />
          <Grid>
            <Col md={6}>
              <Panel>
                <PanelHeader title="Field states" subtitle="Required, optional, hint, error, disabled, read-only" />
                <PanelBody>
                  <Stack gap={6}>
                    <Field label="Required field" required htmlFor="ds-req">
                      {(props) => <Input {...props} placeholder="Placeholder text" />}
                    </Field>

                    <Field
                      label="With hint"
                      optional
                      hint="Helper text stays visible; it is not a placeholder."
                    >
                      {(props) => <Input {...props} leading={Search} placeholder="Search records" />}
                    </Field>

                    <Field label="Validated" required error={nameError} hint="Type one or two characters to see the error state.">
                      {(props) => (
                        <Input
                          {...props}
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          placeholder="Enter a name"
                        />
                      )}
                    </Field>

                    <Field label="Numeric" hint="Tabular figures, so columns of these compare cleanly.">
                      {(props) => <Input {...props} numeric inputMode="decimal" defaultValue="18400.00" />}
                    </Field>

                    <Field label="Disabled" disabled>
                      {(props) => <Input {...props} disabled value="Not editable" readOnly />}
                    </Field>

                    <Field label="Read-only" hint="Distinct from disabled: still selectable and legible.">
                      {(props) => <Input {...props} readOnly value="REF-0000-0000" />}
                    </Field>
                  </Stack>
                </PanelBody>
              </Panel>
            </Col>

            <Col md={6}>
              <Stack gap={6}>
                <Panel>
                  <PanelHeader title="Select, textarea, checkbox" />
                  <PanelBody>
                    <Stack gap={6}>
                      <Field label="Select" required hint="A native select — real platform picker and keyboard behaviour.">
                        {(props) => (
                          <Select
                            {...props}
                            defaultValue=""
                            placeholder="Choose an option"
                            options={[
                              { value: 'a', label: 'First option' },
                              { value: 'b', label: 'Second option' },
                              { value: 'c', label: 'Third option', disabled: true },
                            ]}
                          />
                        )}
                      </Field>

                      <Field label="Select · error" error="Choose an option to continue.">
                        {(props) => (
                          <Select {...props} defaultValue="" placeholder="Choose an option" options={[{ value: 'a', label: 'First option' }]} />
                        )}
                      </Field>

                      <Field label="Textarea" hint="Resizes vertically only.">
                        {(props) => <Textarea {...props} placeholder="Long-form notes" />}
                      </Field>

                      <fieldset className="ds-fieldset">
                        <legend className="ds-fieldset__legend">Options</legend>
                        <Checkbox
                          label="Accept terms"
                          description="20×20 box, 2px radius, indigo when selected."
                          checked={terms}
                          onChange={(e) => setTerms(e.target.checked)}
                        />
                        <Checkbox label="Indeterminate" indeterminate readOnly checked={false} />
                        <Checkbox label="Disabled" disabled />
                      </fieldset>
                    </Stack>
                  </PanelBody>
                  <PanelFooter>
                    <Button variant="quiet">Cancel</Button>
                    <Button variant="accent" disabled={!terms}>Save</Button>
                  </PanelFooter>
                </Panel>

                <Panel>
                  <PanelHeader title="Loading skeleton" subtitle="Reserves the real box, so nothing shifts on arrival" />
                  <PanelBody>
                    <Stack gap={4}>
                      <Skeleton variant="heading" width="60%" />
                      <Skeleton variant="text" />
                      <Skeleton variant="text" width="82%" />
                      <Skeleton variant="control" />
                    </Stack>
                  </PanelBody>
                </Panel>
              </Stack>
            </Col>
          </Grid>
        </Band>

        {/* ---- Panels and stats -------------------------------------------- */}
        <Band tone="sunken">
          <SectionHeader
            index="05 / Surface"
            title="Panels and figures"
            description="Flat by default. The border strengthens and a whisper of shadow appears on hover — but only when the panel is genuinely clickable."
          />
          <Grid>
            <Col md={3}>
              <Panel><PanelBody><Stat label="Throughput" value="1,240" delta="+12.4%" direction="up" caption="vs. previous period" /></PanelBody></Panel>
            </Col>
            <Col md={3}>
              <Panel><PanelBody><Stat label="Latency" value="86ms" delta="−4.1%" direction="down" caption="lower is better" /></PanelBody></Panel>
            </Col>
            <Col md={3}>
              <Panel><PanelBody><Stat label="Backlog" value="512" delta="0.0%" direction="flat" caption="unchanged" /></PanelBody></Panel>
            </Col>
            <Col md={3}>
              <Panel accent><PanelBody><Stat label="Accepted" value="99.2%" delta="+0.3%" direction="up" caption="rolling 30 days" /></PanelBody></Panel>
            </Col>

            <Col md={4}>
              <Panel interactive style={{ padding: 'var(--ds-space-5)' }}>
                <Stack gap={2}>
                  <span className="ds-label">Interactive</span>
                  <p className="ds-panel__title">Hover strengthens the rule</p>
                  <p className="ds-panel__subtitle">Renders as a button, so it is keyboard-reachable.</p>
                </Stack>
              </Panel>
            </Col>
            <Col md={4}>
              <Panel sunken style={{ padding: 'var(--ds-space-5)' }}>
                <Stack gap={2}>
                  <span className="ds-label">Sunken</span>
                  <p className="ds-panel__title">A recessed surface</p>
                  <p className="ds-panel__subtitle">For nesting inside a white panel.</p>
                </Stack>
              </Panel>
            </Col>
            <Col md={4}>
              <Panel>
                <PanelBody flush>
                  <EmptyState
                    compact
                    title="Nothing here yet"
                    description="An empty region always needs a reason and a way out."
                    action={<Button variant="outline" icon={Plus}>Add the first one</Button>}
                  />
                </PanelBody>
              </Panel>
            </Col>
          </Grid>
        </Band>

        {/* ---- Status ------------------------------------------------------ */}
        <Band>
          <SectionHeader
            index="06 / Status"
            title="Status tags"
            description="Compact, almost square, 11px mono. Colour carries status and nothing else, and the text label is always present so meaning survives without colour perception."
          />
          <Stack gap={6}>
            <Stack gap={3}>
              <span className="ds-label">Tinted</span>
              <Cluster gap="8px">
                {TAGS.map((t) => (
                  <StatusTag key={t} variant={t} dot>{t}</StatusTag>
                ))}
              </Cluster>
            </Stack>
            <Stack gap={3}>
              <span className="ds-label">Solid</span>
              <Cluster gap="8px">
                {TAGS.map((t) => (
                  <StatusTag key={t} variant={t} solid>{t}</StatusTag>
                ))}
              </Cluster>
            </Stack>
          </Stack>
        </Band>

        {/* ---- Table ------------------------------------------------------- */}
        <Band tone="sunken">
          <SectionHeader
            index="07 / Data"
            title="Data table"
            description="Sortable mono headers with aria-sort, a header rule darker than the row dividers, and tabular figures in the numeric columns."
            actions={
              <Cluster gap="8px">
                <Button variant="outline" size="sm" onClick={() => setTableLoading((v) => !v)}>
                  {tableLoading ? 'Show rows' : 'Show loading'}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setEmptied((v) => !v)}>
                  {emptied ? 'Restore rows' : 'Show empty'}
                </Button>
              </Cluster>
            }
          />
          <Stack gap={4}>
            <Panel style={{ overflow: 'hidden' }}>
              <Toolbar style={{ borderBottom: 0 }}>
                <Cluster gap="8px">
                  <StatusTag variant="neutral">{emptied ? 0 : ROWS.length} records</StatusTag>
                  <Divider />
                  <span className="ds-label">Sorted by column header</span>
                </Cluster>
                <ToolbarSpacer />
                <IconButton icon={Search} label="Search records" />
                <IconButton icon={Download} label="Export records" />
              </Toolbar>
            </Panel>

            <DataTable
              caption="Specimen records"
              columns={COLUMNS}
              rows={emptied ? [] : ROWS}
              loading={tableLoading}
              emptyTitle="No records match"
              emptyDescription="Loosen the filters, or add the first record."
              emptyAction={<Button variant="outline" icon={Plus}>Add record</Button>}
              footer={
                <tr>
                  <td colSpan={4}>Total</td>
                  <td className="ds-table__cell--numeric">1,862</td>
                  <td className="ds-table__cell--numeric">30,265.00</td>
                </tr>
              }
            />
          </Stack>
        </Band>

        {/* ---- Overlays ---------------------------------------------------- */}
        <Band>
          <SectionHeader
            index="08 / Overlay"
            title="Modals and notifications"
            description="The dialog traps focus, closes on Escape, and hands focus back to whatever opened it. Toasts announce politely and never steal focus."
          />
          <Cluster gap="12px">
            <Button variant="outline" onClick={() => setModalOpen(true)}>Open modal</Button>
            <Button variant="danger-outline" onClick={() => setConfirmOpen(true)}>Destructive action</Button>
            <Button variant="quiet" onClick={() => success('Record saved', { description: 'All changes are on the server.' })}>
              Success toast
            </Button>
            <Button variant="quiet" onClick={() => error('Could not save', { description: 'The connection dropped. Nothing was lost.' })}>
              Error toast
            </Button>
            <Button
              variant="quiet"
              onClick={() =>
                toast({
                  title: 'Record archived',
                  description: 'It will stop appearing in the default view.',
                  variant: 'informative',
                  action: { label: 'Undo', onClick: () => success('Restored') },
                })
              }
            >
              Toast with undo
            </Button>
          </Cluster>
        </Band>

        {/* -- Footer: the second and last place a dark surface is allowed -- */}
        <Band tone="dark" as="footer" size="sm">
          <Stack gap={6}>
            <Rule />
            <Cluster gap="24px">
              <Stack gap={1}>
                <span className="ds-label-micro">System</span>
                <span className="ds-mono">Swiss Modernism 2.0</span>
              </Stack>
              <Stack gap={1}>
                <span className="ds-label-micro">Base unit</span>
                <span className="ds-mono">4px</span>
              </Stack>
              <Stack gap={1}>
                <span className="ds-label-micro">Accent</span>
                <span className="ds-mono">#4F46E5</span>
              </Stack>
              <Stack gap={1}>
                <span className="ds-label-micro">Motion</span>
                <span className="ds-mono">150 / 200 / 300ms</span>
              </Stack>
            </Cluster>
          </Stack>
        </Band>
      </ShellMain>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        eyebrow="Specimen"
        title="Dialog"
        description="Scales in from 0.97, traps focus, and becomes a bottom sheet below 640px."
        footer={
          <>
            <Button variant="quiet" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button variant="accent" onClick={() => { setModalOpen(false); success('Saved') }}>Save</Button>
          </>
        }
      >
        <Stack gap={4}>
          <Field label="Label" required>
            {(props) => <Input {...props} placeholder="Type here — focus should stay put" />}
          </Field>
          <Field label="Notes" optional>
            {(props) => <Textarea {...props} rows={3} placeholder="Optional notes" />}
          </Field>
        </Stack>
      </Modal>

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        loading={confirming}
        title="Delete this record?"
        description="This cannot be undone. Cancel is focused first and the destructive action sits last, away from where muscle memory expects OK."
        confirmLabel="Delete record"
        onConfirm={() => {
          setConfirming(true)
          setTimeout(() => {
            setConfirming(false)
            setConfirmOpen(false)
            success('Record deleted', { action: { label: 'Undo', onClick: () => success('Restored') } })
          }, 900)
        }}
      />
    </ResponsiveShell>
  )
}

export default function DesignSystemShowcase() {
  return (
    <ToastProvider>
      <ShowcaseBody />
    </ToastProvider>
  )
}
