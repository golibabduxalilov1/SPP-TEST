import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { Link } from "react-router-dom";
import { CheckCircle2, Clock, Table2, Terminal } from "lucide-react";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import { PageLoader, EmptyState } from "../../components/ui/Misc";
import SegmentedControl from "../../components/ui/SegmentedControl";
import { format } from "date-fns";
import { useTutorial } from "../../tutorial/TutorialContext";
import { tabloSteps } from "../../tutorial/content/tablo";

const MODES = [
  { key: "hajm", label: "Hajm" },
  { key: "soni", label: "Soni" },
  { key: "foiz", label: "Foiz" },
];

const STATUS_LABEL = {
  in_progress: "Jarayonda",
  blocked: "Bloklangan",
};

const UNIT_LABEL = {
  m2: "m²",
  meter: "m",
  piece: "dona",
  package: "quti",
};

function formatCell(cell, mode) {
  if (cell.status === "not_required" || cell.value === null) return "—";
  if (mode === "foiz") return `${cell.value}%`;
  return cell.value;
}

// Client-side aggregation over the already-fetched table — no extra backend call.
function computeTotals(data, mode) {
  if (!data) return {};
  const totals = {};
  for (const op of data.operations) {
    const values = data.rows
      .map((r) => r.cells[op.code])
      .filter((c) => c && c.status !== "not_required" && c.value !== null)
      .map((c) => c.value);
    if (values.length === 0) {
      totals[op.code] = null;
      continue;
    }
    const sum = values.reduce((a, b) => a + b, 0);
    totals[op.code] = mode === "foiz" ? Math.round(sum / values.length) : Math.round(sum * 100) / 100;
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
  const { registerAndAutoStart } = useTutorial();
  const now = useLiveClock();

  useEffect(() => registerAndAutoStart("tablo", tabloSteps), [registerAndAutoStart]);

  async function load(m) {
    setLoading(true);
    const { data } = await adminApi.get("/production/table", { params: { mode: m } });
    setData(data);
    setLoading(false);
    setLastUpdated(new Date());
  }

  useEffect(() => {
    load(mode);
    const interval = setInterval(() => load(mode), 20000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  const totals = useMemo(() => computeTotals(data, mode), [data, mode]);
  const activeOrders = data?.rows?.length ?? 0;

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
              className="!min-h-11 !rounded-lg !border-white/15 !bg-white/10 !text-sm !font-medium !text-white/80 hover:!bg-white/15 hover:!text-white"
            >
              <Terminal size={14} /> Terminal
            </Button>
            <span className="tabular flex min-h-11 items-center rounded-lg border border-white/12 bg-white/8 px-3 text-sm font-semibold text-white/85">
              {format(now, "HH:mm:ss")}
            </span>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader
          data-tutorial="tablo-legend"
          title="Tablo"
          subtitle="Yashil — bajarilgan, sariq — jarayonda, qizil — bloklangan, kulrang — kerak emas"
        />
        <CardBody data-tutorial="tablo-table" className="p-0">
          {loading || !data ? (
            <PageLoader />
          ) : data.rows.length === 0 ? (
            <EmptyState title="Aktiv buyurtma yo'q" />
          ) : (
            <Table className="min-w-225!" label="Ishlab chiqarish tablosi">
                <thead className="sticky top-0 bg-(--surface-muted) text-xs tracking-wide text-(--ink-soft) uppercase">
                  <tr>
                    <th className="sticky left-0 z-10 w-10 min-w-10 bg-(--surface-muted) px-3 py-3 text-left font-semibold">№</th>
                    <th className="sticky left-10 z-10 min-w-55 bg-(--surface-muted) px-3 py-3 text-left font-semibold">Buyurtma</th>
                    <th className="px-3 py-3 text-left font-semibold">Muddat</th>
                    {data.operations.map((op) => (
                      <th key={op.code} className="min-w-25 px-3 py-3 text-center font-semibold">{op.name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-(--border-subtle) bg-(--surface)">
                  <tr className="bg-(--accent-soft)">
                    <td className="sticky left-0 z-10 w-10 min-w-10 bg-(--accent-soft)" />
                    <td className="sticky left-10 z-10 min-w-55 bg-(--accent-soft) px-3 py-3 text-xs font-semibold tracking-wide text-(--accent-strong) uppercase">
                      Jami detallar
                    </td>
                    <td />
                    {data.operations.map((op) => (
                      <td key={op.code} className="px-3 py-3 text-center">
                        <p className="tabular text-base font-bold text-(--accent-strong)">
                          {totals[op.code] === null ? "—" : totals[op.code]}
                        </p>
                        {totals[op.code] !== null && mode !== "foiz" && (
                          <p className="text-[10px] font-medium text-(--ink-faint)">{UNIT_LABEL[op.measure_unit] || op.measure_unit}</p>
                        )}
                      </td>
                    ))}
                  </tr>
                  {data.rows.map((row) => (
                    <tr key={row.order_id} className="transition-colors hover:bg-(--accent-soft)">
                      <td className="sticky left-0 z-10 w-10 min-w-10 bg-(--surface) px-3 py-3">{row.index}</td>
                      <td className="sticky left-10 z-10 min-w-55 bg-(--surface) px-3 py-3">
                        <p className="font-semibold">#{row.order_no}</p>
                        <p className="text-xs text-(--ink-faint)">{row.customer_name || row.product_name}</p>
                      </td>
                      <td className="px-3 py-3 text-xs">{row.deadline ? format(new Date(row.deadline), "dd.MM.yyyy") : "—"}</td>
                      {data.operations.map((op) => {
                        const cell = row.cells[op.code];
                        return (
                          <td key={op.code} className="p-1.5 text-center">
                            {cell.status === "completed" ? (
                              <div className="flex min-h-12 items-center justify-center rounded-lg bg-status-green text-white">
                                <CheckCircle2 size={18} />
                              </div>
                            ) : cell.status === "not_required" ? (
                              <div className="flex min-h-12 items-center justify-center rounded-lg bg-(--surface-muted) text-(--ink-faint)">
                                —
                              </div>
                            ) : (
                              <div
                                className={clsx(
                                  "flex min-h-12 flex-col items-center justify-center gap-0.5 rounded-lg px-2 py-1.5",
                                  cell.status === "in_progress" ? "bg-status-yellow-bg" : "bg-status-red-bg"
                                )}
                              >
                                <p className={clsx("tabular text-sm font-bold", cell.status === "in_progress" ? "text-status-yellow" : "text-status-red")}>
                                  {formatCell(cell, mode)}
                                </p>
                                <p className={clsx("text-[10px] font-medium opacity-70", cell.status === "in_progress" ? "text-status-yellow" : "text-status-red")}>
                                  {STATUS_LABEL[cell.status]}
                                </p>
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
