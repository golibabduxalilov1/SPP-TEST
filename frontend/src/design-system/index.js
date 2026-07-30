/* ============================================================================
   SWISS MODERNISM 2.0 — DESIGN SYSTEM
   ----------------------------------------------------------------------------
   Import from here and nowhere else (this project has no path alias, so the
   import is relative to the importing file):

     import { ResponsiveShell, Button, DataTable } from '../design-system'

   Importing this module is what pulls in the fonts and the stylesheets. Nothing
   is registered globally beyond that: every rule is scoped to the `.ds` root
   class that <ResponsiveShell> applies, so the host app's own theme is
   untouched. Do not add these files to src/index.css.
   ============================================================================ */

import '@fontsource-variable/space-grotesk'
import '@fontsource-variable/inter'
import '@fontsource-variable/jetbrains-mono'

import './tokens.css'
import './components.css'

export { Button, IconButton } from './components/Button.jsx'
export { Field, Input, Textarea } from './components/Field.jsx'
export { Select } from './components/Select.jsx'
export { Checkbox } from './components/Checkbox.jsx'
export { Panel, PanelHeader, PanelBody, PanelFooter, Stat } from './components/Panel.jsx'
export { StatusTag } from './components/StatusTag.jsx'
export { DataTable } from './components/DataTable.jsx'
export { Skeleton, SkeletonText, SkeletonRegion } from './components/Skeleton.jsx'
export { EmptyState } from './components/EmptyState.jsx'
export { Modal, ConfirmDialog } from './components/Modal.jsx'
export { ToastProvider, Toast, useToast } from './components/Toast.jsx'
export { PageHeader, SectionHeader, Breadcrumbs } from './components/PageHeader.jsx'
export {
  ResponsiveShell,
  ShellMain,
  Container,
  Band,
  Grid,
  Col,
  Stack,
  Cluster,
  Rule,
  Toolbar,
  ToolbarSpacer,
  Divider,
} from './components/ResponsiveShell.jsx'
