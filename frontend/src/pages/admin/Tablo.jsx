import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import clsx from "clsx";
import { Link } from "react-router-dom";
import { CheckCircle2, CircleAlert, Clock, Maximize2, Minimize2, Table2, Terminal, Zap } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody } from "../../components/ui/Card";
import { Table } from "../../components/ui/Table";
import ProgressBar, { computeProgressPercent } from "../../components/ui/ProgressBar";
import Button from "../../components/ui/Button";
import { PageLoader, EmptyState } from "../../components/ui/Misc";
import SegmentedControl from "../../components/ui/SegmentedControl";
import { format } from "date-fns";
import { useTutorial } from "../../tutorial/TutorialContext";
import { tabloSteps } from "../../tutorial/content/tablo";

// Icon + label for each priority. "normal" renders nothing.
const PRIORITY_ICONS = {
  high: { Icon: Zap, label: "Tezkor", className: "fill-status-orange text-status-orange" },
  urgent: { Icon: CircleAlert, label: "Shoshilinch", className: "text-status-red" },
};

// Compact priority marker shown left of the product name. Click/tap toggles a
// tooltip (desktop also gets hover/focus); portals into `portalTarget` and
// positions itself via getBoundingClientRect so it escapes the row's
// overflow-hidden/truncate ancestors and the table's horizontal scroll clip.
function PriorityMark({ priority, portalTarget }) {
  const meta = PRIORITY_ICONS[priority];
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState(null);
  const pinnedRef = useRef(false);
  const buttonRef = useRef(null);
  const tooltipRef = useRef(null);
  const tooltipId = useId();

  const close = () => {
    pinnedRef.current = false;
    setOpen(false);
  };

  useLayoutEffect(() => {
    if (!open || !buttonRef.current) return;
    const place = () => {
      const rect = buttonRef.current.getBoundingClientRect();
      const tipHeight = tooltipRef.current?.offsetHeight ?? 28;
      const gap = 6;
      const above = rect.top - tipHeight - gap >= 0;
      setCoords({
        left: rect.left + rect.width / 2,
        top: above ? rect.top - gap : rect.bottom + gap,
        placement: above ? "above" : "below",
      });
    };
    place();
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onOutside = (event) => {
      if (buttonRef.current && !buttonRef.current.contains(event.target)) close();
    };
    document.addEventListener("mousedown", onOutside);
    document.addEventListener("touchstart", onOutside);
    return () => {
      document.removeEventListener("mousedown", onOutside);
      document.removeEventListener("touchstart", onOutside);
    };
  }, [open]);

  if (!meta) return null;
  const { Icon, label, className } = meta;

  return (
    <>
      <button
        type="button"
        ref={buttonRef}
        aria-label={label}
        aria-describedby={open ? tooltipId : undefined}
        className="inline-flex shrink-0 cursor-pointer items-center justify-center rounded-sm leading-none outline-none focus-visible:ring-2 focus-visible:ring-(--accent)"
        onClick={(event) => {
          event.stopPropagation();
          if (pinnedRef.current) {
            close();
          } else {
            pinnedRef.current = true;
            setOpen(true);
          }
        }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => {
          if (!pinnedRef.current) setOpen(false);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          if (!pinnedRef.current) setOpen(false);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape" && open) {
            event.stopPropagation();
            close();
          }
        }}
      >
        <Icon size={13} className={className} aria-hidden="true" />
      </button>
      {open &&
        coords &&
        createPortal(
          <span
            ref={tooltipRef}
            id={tooltipId}
            role="tooltip"
            className="tooltip-fade-in pointer-events-none fixed rounded-md bg-(--ink) px-2 py-1 text-xs font-medium whitespace-nowrap text-white shadow-lg"
            style={{
              left: coords.left,
              top: coords.top,
              zIndex: 9999,
              transform: `translate(-50%, ${coords.placement === "above" ? "-100%" : "0"})`,
            }}
          >
            {label}
          </span>,
          portalTarget || document.body
        )}
    </>
  );
}

// Pixel widths for the sticky/frozen "№", product and deadline columns.
// Operation ("jarayon") columns are intentionally left unsized so table-auto
// shrinks them to their content (name/value) instead of a generous fixed width.
const COL_W = { index: 64, product: 190, deadline: 96 };

const MODES = [
  { key: "hajm", label: "Hajm" },
  { key: "soni", label: "Soni" },
];

const STATUS_LABEL = {
  in_progress: "Jarayonda",
  pending: "Kutilmoqda",
  completed: "Bajarilgan",
  blocked: "Bloklangan",
};

// Tablo-only display shortening — full unit words take too much room in a
// dense cell. Keyed by measure_unit (see backend/manufacturing/units.py
// MEASURE_UNIT_CHOICES); anything not listed here falls back to unit_label
// as-is so a newly added unit still renders instead of disappearing.
const UNIT_ABBR = {
  meter: "m", // chiziqli metr
  m2: "m²", // yuza (kvadrat metr) — already short, kept for clarity
  package: "qad.", // qadoq
  piece: "dona", // no shorter standard form without losing clarity
};

// Mirrors backend/core/tablo.py::_stage_value — Hajm shows each stage's own
// unit (from its measure_unit, via the API's unit_label), Soni is always
// dona, Foiz has no unit.
function displayUnit(op, mode) {
  if (mode === "foiz") return null;
  if (mode === "soni") return "dona";
  return UNIT_ABBR[op.measure_unit] || op.unit_label;
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

// Foiz mode already carries the percent directly (cell.value); Hajm/Soni
// derive it from completed/total, which safely resolves to 0% when the
// stage has no plan yet (see computeProgressPercent).
function stageProgressPercent(cell, mode) {
  if (mode === "foiz") return Math.min(100, Math.max(0, cell.value ?? 0));
  return computeProgressPercent(cell.completed, cell.total);
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

// Fullscreen isn't available in every browser (notably iOS Safari) — checked
// once at module load so the button can hide itself instead of dead-clicking.
const FULLSCREEN_SUPPORTED =
  typeof document !== "undefined" && Boolean(document.fullscreenEnabled || document.webkitFullscreenEnabled);

export default function Tablo() {
  const [mode, setMode] = useState("hajm");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);
  const { registerAndAutoStart } = useTutorial();
  const now = useLiveClock();

  useEffect(() => registerAndAutoStart("tablo", tabloSteps), [registerAndAutoStart]);

  // Syncs state on Esc, on browser-chrome exits, and after our own toggle —
  // covers every way fullscreen can end, not just the button.
  useEffect(() => {
    function syncFullscreen() {
      const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
      setIsFullscreen(Boolean(fsEl) && fsEl === containerRef.current);
    }
    document.addEventListener("fullscreenchange", syncFullscreen);
    document.addEventListener("webkitfullscreenchange", syncFullscreen);
    return () => {
      document.removeEventListener("fullscreenchange", syncFullscreen);
      document.removeEventListener("webkitfullscreenchange", syncFullscreen);
    };
  }, []);

  async function toggleFullscreen() {
    const el = containerRef.current;
    if (!el) return;
    try {
      if (!document.fullscreenElement && !document.webkitFullscreenElement) {
        const request = el.requestFullscreen || el.webkitRequestFullscreen;
        await request?.call(el);
      } else {
        const exit = document.exitFullscreen || document.webkitExitFullscreen;
        await exit?.call(document);
      }
    } catch {
      toast.error("To'liq ekran rejimiga o'tishda xatolik yuz berdi");
    }
  }

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

  useEffect(() => {
    load(mode);
    const interval = setInterval(() => load(mode, false), 20000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  const totals = useMemo(() => computeTotals(data, mode), [data, mode]);
  const activeOrders = data?.rows?.filter((row) => row.stage_status === "in_progress").length ?? 0;

  return (
    <div
      ref={containerRef}
      className={clsx(
        "space-y-6",
        isFullscreen && "flex h-dvh! w-dvw! flex-col overflow-hidden bg-(--canvas) p-4 sm:p-6"
      )}
    >
      {/* Kiosk-style header panel — dark walnut shell, mirrors TerminalLayout's header idiom */}
      <div className="brand-shell relative isolate shrink-0 overflow-hidden rounded-2xl border border-white/8 px-4 py-4 elevation-lg sm:px-6">
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
            {FULLSCREEN_SUPPORTED && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                magnetic={false}
                onClick={toggleFullscreen}
                aria-pressed={isFullscreen}
                aria-label={isFullscreen ? "To'liq ekrandan chiqish" : "To'liq ekran rejimiga o'tish"}
                className={clsx(
                  "min-h-11! rounded-lg! text-sm! font-medium!",
                  isFullscreen
                    ? "border-transparent! bg-[linear-gradient(135deg,var(--accent-2-bright),var(--accent-2))]! text-[#2A1D14]! hover:brightness-105!"
                    : "border-white/15! bg-white/10! text-white/80! hover:bg-white/15! hover:text-white!"
                )}
              >
                {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                {isFullscreen ? "Chiqish" : "To'liq ekran"}
              </Button>
            )}
            <span className="tabular flex min-h-11 items-center rounded-lg border border-white/12 bg-white/8 px-3 text-sm font-semibold text-white/85">
              {format(now, "HH:mm:ss")}
            </span>
          </div>
        </div>
      </div>

      <Card data-tutorial="tablo-legend" className={clsx(isFullscreen && "flex min-h-0 flex-1 flex-col overflow-hidden")}>
        <CardBody data-tutorial="tablo-table" className={clsx("p-0", isFullscreen && "flex min-h-0 flex-1 flex-col")}>
          {loading || !data ? (
            <PageLoader />
          ) : (
            <Table
              className="w-auto! border-collapse text-sm"
              containerClassName={clsx("rounded-2xl", isFullscreen && "min-h-0 flex-1 overflow-y-auto")}
              label="Ishlab chiqarish tablosi"
            >
                <colgroup>
                  <col style={{ width: COL_W.index }} />
                  <col style={{ width: COL_W.product }} />
                  <col style={{ width: COL_W.deadline }} />
                  {data.operations.map((op) => (
                    <col key={op.code} />
                  ))}
                </colgroup>
                <thead className="sticky top-0 z-20 bg-(--surface-muted) text-xs font-bold tracking-[0.08em] text-(--ink-soft) uppercase">
                  <tr>
                    <th className="sticky left-0 z-30 border-r border-b border-(--border-strong) bg-(--surface-muted) px-3 py-4 text-center align-middle">№</th>
                    <th className="border-r border-b border-(--border-strong) bg-(--surface-muted) py-4 pl-3 pr-1 text-left align-middle">
                      Mahsulot turi
                    </th>
                    <th className="border-r border-b border-(--border-strong) bg-(--surface-muted) px-2 py-4 text-center align-middle whitespace-nowrap">
                      Muddat
                    </th>
                    {data.operations.map((op) => (
                      <th key={op.code} className="border-r border-b border-(--border-strong) px-1.5 py-4 text-center align-middle last:border-r-0">
                        <span className="leading-snug whitespace-nowrap" title={op.name}>{op.name}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-(--surface)">
                  <tr className="bg-(--accent-soft)">
                    <td className="sticky left-0 z-10 border-r border-b border-(--border-strong) bg-(--accent-soft) px-3 py-3.5" />
                    <td className="truncate border-r border-b border-(--border-strong) bg-(--accent-soft) py-3.5 pl-3 pr-1 text-xs font-bold tracking-[0.08em] text-(--accent-strong) uppercase">
                      Jami detallar
                    </td>
                    <td className="border-r border-b border-(--border-strong) bg-(--accent-soft)" />
                    {data.operations.map((op) => (
                      <td key={op.code} className="border-r border-b border-(--border-strong) px-1.5 py-3.5 text-center align-middle last:border-r-0">
                        <p className="tabular text-base font-extrabold whitespace-nowrap text-(--accent-strong)">
                          {totals[op.code] === null
                            ? "—"
                            : mode === "foiz"
                            ? `${totals[op.code].value}%`
                            : `${totals[op.code].completed}/${totals[op.code].remaining}`}
                        </p>
                        {totals[op.code] !== null && displayUnit(op, mode) && (
                          <p className="mt-0.5 text-[10px] font-semibold tracking-wide text-(--ink-faint) uppercase">{displayUnit(op, mode)}</p>
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
                    <tr key={row.order_id} className="border-b border-(--border-strong)">
                      <td className="sticky left-0 z-10 border-r border-b border-(--border-strong) bg-(--surface) px-3 py-4 text-center align-middle text-sm text-(--ink-soft)">
                        {row.index}
                      </td>
                      <td className="border-r border-b border-(--border-strong) bg-(--surface) py-4 pl-3 pr-1 align-middle">
                        <p className="flex items-center gap-1.5 overflow-hidden text-sm leading-snug font-semibold whitespace-nowrap" title={row.product_name || "Mahsulot ko'rsatilmagan"}>
                          <PriorityMark priority={row.priority} portalTarget={containerRef.current} />
                          <span className="min-w-0 flex-1 truncate">{row.product_name || "Mahsulot ko'rsatilmagan"}</span>
                        </p>
                      </td>
                      <td className="border-r border-b border-(--border-strong) bg-(--surface) px-2 py-4 text-center align-middle text-sm whitespace-nowrap text-(--ink-soft)">
                        {row.deadline ? format(new Date(row.deadline), "dd.MM.yyyy") : "—"}
                      </td>
                      {data.operations.map((op) => {
                        const cell = row.cells[op.code];
                        return (
                          <td
                            key={op.code}
                            className={clsx(
                              "border-r border-b border-(--border-strong) px-1.5 py-2 text-center align-middle last:border-r-0",
                              cell.status === "completed" && "bg-status-green",
                              cell.status === "in_progress" && "bg-status-yellow-bg",
                              cell.status === "pending" && "bg-status-yellow-bg",
                              cell.status !== "completed" &&
                                cell.status !== "in_progress" &&
                                cell.status !== "pending" &&
                                cell.status !== "not_required" &&
                                "bg-status-red"
                            )}
                          >
                            {cell.status === "completed" ? (
                              <div
                                className="flex min-h-16 flex-col items-center justify-center gap-1"
                                title={`${formatCell(cell, op, mode)} — ${STATUS_LABEL.completed}`}
                              >
                                <CheckCircle2 size={20} className="shrink-0 text-white" strokeWidth={2.25} />
                                <ProgressBar
                                  percent={stageProgressPercent(cell, mode)}
                                  amountLabel={formatCell(cell, op, mode)}
                                  className="px-1 text-white"
                                />
                              </div>
                            ) : cell.status === "not_required" ? (
                              <div className="flex min-h-16 flex-col items-center justify-center text-(--ink-faint)">
                                <span className="text-base">—</span>
                              </div>
                            ) : cell.status === "pending" ? (
                              <div className="flex min-h-16 flex-col items-center justify-center gap-1">
                                {/* Foiz keeps its original dash-only pending display; only Hajm/Soni show 0/total. */}
                                <p className="tabular text-base leading-tight font-bold whitespace-nowrap text-status-yellow">
                                  {mode === "foiz" ? "—" : formatCell(cell, op, mode)}
                                </p>
                                <ProgressBar percent={stageProgressPercent(cell, mode)} className="px-1 text-status-yellow" />
                              </div>
                            ) : (
                              <div className="flex min-h-16 flex-col items-center justify-center gap-1">
                                <p
                                  className={clsx(
                                    "tabular text-base leading-tight font-bold whitespace-nowrap",
                                    cell.status === "in_progress" ? "text-status-yellow" : "text-white"
                                  )}
                                >
                                  {formatCell(cell, op, mode)}
                                </p>
                                {cell.status !== "in_progress" && (
                                  <p className="text-[11px] leading-tight font-semibold text-white/85">{STATUS_LABEL[cell.status]}</p>
                                )}
                                <ProgressBar
                                  percent={stageProgressPercent(cell, mode)}
                                  className={clsx("px-1", cell.status === "in_progress" ? "text-status-yellow" : "text-white")}
                                />
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
