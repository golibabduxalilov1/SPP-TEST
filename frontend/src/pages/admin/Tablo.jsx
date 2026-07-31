import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { Link } from "react-router-dom";
import { CheckCircle2, CircleAlert, Clock, Table2, Terminal, Zap } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { useAuthStore } from "../../store/authStore";
import { Card, CardBody } from "../../components/ui/Card";
import { Table } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import { PageLoader, EmptyState } from "../../components/ui/Misc";
import SegmentedControl from "../../components/ui/SegmentedControl";
import { format } from "date-fns";
import { useTutorial } from "../../tutorial/TutorialContext";
import { tabloSteps } from "../../tutorial/content/tablo";
import { PRIORITY_LABELS } from "../../constants/labels";

// Compact priority marker shown left of the product name. "normal" renders nothing.
function PriorityMark({ priority }) {
  if (priority === "urgent") {
    return (
      <Zap
        size={13}
        className="shrink-0 fill-status-red text-status-red"
        aria-label={PRIORITY_LABELS.urgent}
        title={PRIORITY_LABELS.urgent}
      />
    );
  }
  if (priority === "high") {
    return (
      <CircleAlert
        size={13}
        className="shrink-0 text-status-orange"
        aria-label={PRIORITY_LABELS.high}
        title={PRIORITY_LABELS.high}
      />
    );
  }
  return null;
}

// Fixed pixel widths for the sticky/frozen columns and each process column —
// COL_LEFT offsets are derived from COL_W so sticky `left` values always match.
const COL_W = { index: 48, product: 200, deadline: 120, op: 140 };
const COL_LEFT = { product: COL_W.index, deadline: COL_W.index + COL_W.product };

const MODES = [
  { key: "hajm", label: "Hajm" },
  { key: "soni", label: "Soni" },
  { key: "foiz", label: "Foiz" },
];

const STATUS_LABEL = {
  in_progress: "Jarayonda",
  pending: "Kutilmoqda",
  completed: "Bajarilgan",
  blocked: "Bloklangan",
};

const COMPLETE_STAGE_ROLES = ["super_admin", "admin", "director", "manager", "master", "technologist"];

// Mirrors backend/core/tablo.py::_stage_value — Hajm shows each stage's own
// unit (from its measure_unit, via the API's unit_label), Soni is always
// dona, Foiz has no unit.
function displayUnit(op, mode) {
  if (mode === "foiz") return null;
  if (mode === "soni") return "dona";
  return op.unit_label;
}

// Every non-Foiz cell is shown as "Bajarilgan/Qolgan" (completed/remaining),
// e.g. "3/7 dona" or "4.5/8.5 m²" — mirrors backend/core/tablo.py::_stage_progress.
function formatCell(cell, op, mode) {
  if (cell.status === "not_required") return "—";
  if (mode === "foiz") return `${cell.value}%`;
  const unit = displayUnit(op, mode);
  const fraction = `${cell.completed}/${cell.remaining}`;
  return unit ? `${fraction} ${unit}` : fraction;
}

// Client-side aggregation over the already-fetched table — no extra backend call.
function computeTotals(data, mode) {
  if (!data) return {};
  const totals = {};
  for (const op of data.operations) {
    const cells = data.rows.map((r) => r.cells[op.code]).filter((c) => c && c.status !== "not_required");
    if (cells.length === 0) {
      totals[op.code] = null;
      continue;
    }
    if (mode === "foiz") {
      const sum = cells.reduce((acc, c) => acc + c.value, 0);
      totals[op.code] = { value: Math.round(sum / cells.length) };
    } else {
      const completed = cells.reduce((acc, c) => acc + c.completed, 0);
      const remaining = cells.reduce((acc, c) => acc + c.remaining, 0);
      totals[op.code] = {
        completed: Math.round(completed * 100) / 100,
        remaining: Math.round(remaining * 100) / 100,
      };
    }
  }
  return totals;
}

function useLiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export default function Tablo() {
  const [mode, setMode] = useState("hajm");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [completingId, setCompletingId] = useState(null);
  const user = useAuthStore((state) => state.user);
  const { registerAndAutoStart } = useTutorial();
  const now = useLiveClock();

  useEffect(() => registerAndAutoStart("tablo", tabloSteps), [registerAndAutoStart]);

  const canCompleteStage = Boolean(
    user?.is_superuser || user?.role === "super_admin" || COMPLETE_STAGE_ROLES.includes(user?.role)
  );

  async function load(m, showLoader = true) {
    if (showLoader) setLoading(true);
    try {
      const { data } = await adminApi.get("/production/table", { params: { mode: m } });
      setData(data);
      setLastUpdated(new Date());
    } catch (error) {
      if (showLoader) toast.error(error.response?.data?.detail || "Tabloni yuklashda xatolik yuz berdi");
    } finally {
      if (showLoader) setLoading(false);
    }
  }

  async function completeStage(row) {
    setCompletingId(row.order_id);
    try {
      const { data: order } = await adminApi.post(`/orders/${row.order_id}/complete-current-stage/`);
      toast.success(
        order.current_stage_name
          ? `Keyingi bosqich: ${order.current_stage_name}`
          : `#${row.order_no} ishlab chiqarishi tugallandi`
      );
      await load(mode, false);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Bosqichni yakunlashda xatolik yuz berdi");
    } finally {
      setCompletingId(null);
    }
  }

  useEffect(() => {
    load(mode);
    const interval = setInterval(() => load(mode, false), 20000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  const totals = useMemo(() => computeTotals(data, mode), [data, mode]);
  const activeOrders = data?.rows?.filter((row) => row.stage_status === "in_progress").length ?? 0;

  return (
    <div className="space-y-6">
      {/* Kiosk-style header panel — dark walnut shell, mirrors TerminalLayout's header idiom */}
      <div className="brand-shell relative isolate overflow-hidden rounded-2xl border border-white/8 px-4 py-4 elevation-lg sm:px-6">
        <div className="relative z-1 grid grid-cols-1 items-center gap-4 sm:grid-cols-[minmax(0,1fr)_auto] xl:grid-cols-[minmax(13rem,1fr)_auto_auto]">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[linear-gradient(135deg,var(--accent-2-bright),var(--accent-2))] text-[#2A1D14] shadow-(--shadow-accent)">
              <Table2 size={22} />
            </span>
            <div className="min-w-0">
              <p className="font-display text-base font-semibold leading-tight text-white sm:text-lg">Ishlab chiqarish tablosi</p>
              <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-white/45">Miqdor nazorati</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <span className="flex min-h-8 items-center gap-1.5 rounded-full border border-status-green/15 bg-status-green-bg px-2.5 py-1 text-xs font-semibold text-status-green">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-status-green opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-status-green" />
              </span>
              Jonli · {activeOrders} buyurtma
            </span>

            {lastUpdated && (
              <span className="hidden min-h-8 items-center gap-1.5 rounded-full border border-white/12 bg-white/8 px-2.5 py-1 text-xs text-white/55 sm:flex">
                <Clock size={12} /> Yangilangan: {format(lastUpdated, "HH:mm:ss")}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3 sm:col-span-2 xl:col-span-1">
            <div data-tutorial="tablo-mode">
              <SegmentedControl
                options={MODES.map((m) => ({ value: m.key, label: m.label }))}
                value={mode}
                onChange={setMode}
              />
            </div>
            <Button
              as={Link}
              to="/terminal/login"
              variant="ghost"
              size="sm"
              magnetic={false}
              className="min-h-11! rounded-lg! border-white/15! bg-white/10! text-sm! font-medium! text-white/80! hover:bg-white/15! hover:text-white!"
            >
              <Terminal size={14} /> Terminal
            </Button>
            <span className="tabular flex min-h-11 items-center rounded-lg border border-white/12 bg-white/8 px-3 text-sm font-semibold text-white/85">
              {format(now, "HH:mm:ss")}
            </span>
          </div>
        </div>
      </div>

      <Card data-tutorial="tablo-legend">
        <CardBody data-tutorial="tablo-table" className="p-0">
          {loading || !data ? (
            <PageLoader />
          ) : (
            <Table
              className="table-fixed! border-collapse text-sm"
              containerClassName="rounded-2xl"
              style={{ width: COL_W.index + COL_W.product + COL_W.deadline + data.operations.length * COL_W.op }}
              label="Ishlab chiqarish tablosi"
            >
                <colgroup>
                  <col style={{ width: COL_W.index }} />
                  <col style={{ width: COL_W.product }} />
                  <col style={{ width: COL_W.deadline }} />
                  {data.operations.map((op) => (
                    <col key={op.code} style={{ width: COL_W.op }} />
                  ))}
                </colgroup>
                <thead className="sticky top-0 z-20 bg-(--surface-muted) text-[11px] font-semibold tracking-wide text-(--ink-soft) uppercase">
                  <tr>
                    <th className="sticky left-0 z-30 border-r border-b border-(--border-subtle) bg-(--surface-muted) px-2 py-2 text-center align-middle">№</th>
                    <th
                      className="sticky z-30 border-r border-b border-(--border-subtle) bg-(--surface-muted) px-3 py-2 text-left align-middle"
                      style={{ left: COL_LEFT.product }}
                    >
                      Mahsulot turi
                    </th>
                    <th
                      className="sticky z-30 border-r border-b border-(--border) bg-(--surface-muted) px-2 py-2 text-center align-middle shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)]"
                      style={{ left: COL_LEFT.deadline }}
                    >
                      Muddat
                    </th>
                    {data.operations.map((op) => (
                      <th key={op.code} className="border-r border-b border-(--border-subtle) px-2 py-2 text-center align-middle last:border-r-0">
                        <span className="line-clamp-2 leading-tight" title={op.name}>{op.name}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-(--surface)">
                  <tr className="bg-(--accent-soft)">
                    <td className="sticky left-0 z-10 border-r border-b border-(--border-subtle) bg-(--accent-soft) px-2 py-2" />
                    <td
                      className="sticky z-10 truncate border-r border-b border-(--border-subtle) bg-(--accent-soft) px-3 py-2 text-xs font-semibold tracking-wide text-(--accent-strong) uppercase"
                      style={{ left: COL_LEFT.product }}
                    >
                      Jami detallar
                    </td>
                    <td
                      className="sticky z-10 border-r border-b border-(--border) bg-(--accent-soft) shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)]"
                      style={{ left: COL_LEFT.deadline }}
                    />
                    {data.operations.map((op) => (
                      <td key={op.code} className="border-r border-b border-(--border-subtle) px-2 py-2 text-center last:border-r-0">
                        <p className="tabular text-sm font-bold whitespace-nowrap text-(--accent-strong)">
                          {totals[op.code] === null
                            ? "—"
                            : mode === "foiz"
                            ? `${totals[op.code].value}%`
                            : `${totals[op.code].completed}/${totals[op.code].remaining}`}
                        </p>
                        {totals[op.code] !== null && displayUnit(op, mode) && (
                          <p className="text-[10px] font-medium text-(--ink-faint)">{displayUnit(op, mode)}</p>
                        )}
                      </td>
                    ))}
                  </tr>
                  {data.rows.length === 0 && (
                    <tr>
                      <td colSpan={3 + data.operations.length} className="px-3 py-10">
                        <EmptyState title="Hozircha faol buyurtmalar yo'q" />
                      </td>
                    </tr>
                  )}
                  {data.rows.map((row) => (
                    <tr key={row.order_id} className="group border-b border-(--border-subtle) transition-colors hover:bg-(--accent-soft)">
                      <td className="sticky left-0 z-10 border-r border-b border-(--border-subtle) bg-(--surface) px-2 py-2 text-center text-xs text-(--ink-soft) group-hover:bg-(--accent-soft)">
                        {row.index}
                      </td>
                      <td
                        className="sticky z-10 border-r border-b border-(--border-subtle) bg-(--surface) px-3 py-2 group-hover:bg-(--accent-soft)"
                        style={{ left: COL_LEFT.product }}
                      >
                        <p className="flex items-center gap-1 truncate text-sm font-semibold" title={row.product_name || "Mahsulot ko'rsatilmagan"}>
                          <PriorityMark priority={row.priority} />
                          <span className="truncate">{row.product_name || "Mahsulot ko'rsatilmagan"}</span>
                        </p>
                      </td>
                      <td
                        className="sticky z-10 truncate border-r border-b border-(--border) bg-(--surface) px-2 py-2 text-center text-xs text-(--ink-soft) shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)] group-hover:bg-(--accent-soft)"
                        style={{ left: COL_LEFT.deadline }}
                      >
                        {row.deadline ? format(new Date(row.deadline), "dd.MM.yyyy") : "—"}
                      </td>
                      {data.operations.map((op) => {
                        const cell = row.cells[op.code];
                        return (
                          <td key={op.code} className="border-r border-b border-(--border-subtle) px-1.5 py-1.5 text-center align-middle last:border-r-0">
                            {cell.status === "completed" ? (
                              <div className="flex min-h-11 flex-col items-center justify-center gap-0.5 border-l-2 border-status-green pl-1.5">
                                <p className="tabular flex items-center gap-1 text-sm font-bold whitespace-nowrap text-status-green">
                                  <CheckCircle2 size={13} className="shrink-0" />
                                  {formatCell(cell, op, mode)}
                                </p>
                                <p className="text-[10px] font-medium text-status-green/75">{STATUS_LABEL.completed}</p>
                              </div>
                            ) : cell.status === "not_required" ? (
                              <div className="flex min-h-11 flex-col items-center justify-center text-(--ink-faint)">
                                <span className="text-sm">—</span>
                              </div>
                            ) : cell.status === "pending" ? (
                              <div className="flex min-h-11 flex-col items-center justify-center gap-0.5 text-(--ink-faint)">
                                {/* Foiz keeps its original dash-only pending display; only Hajm/Soni show 0/total. */}
                                <p className="tabular text-sm font-semibold whitespace-nowrap">{mode === "foiz" ? "—" : formatCell(cell, op, mode)}</p>
                                <span className="text-[10px] font-medium">{STATUS_LABEL.pending}</span>
                              </div>
                            ) : (
                              <div
                                className={clsx(
                                  "flex min-h-11 flex-col items-center justify-center gap-0.5 border-l-2 pl-1.5",
                                  cell.status === "in_progress" ? "border-status-yellow" : "border-status-red"
                                )}
                              >
                                <p className={clsx("tabular text-sm font-bold whitespace-nowrap", cell.status === "in_progress" ? "text-status-yellow" : "text-status-red")}>
                                  {formatCell(cell, op, mode)}
                                </p>
                                <p className={clsx("text-[10px] font-medium opacity-70", cell.status === "in_progress" ? "text-status-yellow" : "text-status-red")}>
                                  {STATUS_LABEL[cell.status]}
                                </p>
                                {cell.status === "in_progress" && canCompleteStage && (
                                  <button
                                    type="button"
                                    onClick={() => completeStage(row)}
                                    disabled={completingId === row.order_id}
                                    className="focus-ring mt-0.5 min-h-6.5 rounded border border-status-yellow/30 px-1.5 py-0.5 text-[10px] leading-tight font-semibold text-status-yellow transition-colors hover:bg-status-yellow-bg disabled:pointer-events-none disabled:opacity-50"
                                  >
                                    {completingId === row.order_id ? "Yakunlanmoqda..." : "Yakunlash"}
                                  </button>
                                )}
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
            </Table>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
