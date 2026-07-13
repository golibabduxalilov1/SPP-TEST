import { useEffect, useState } from "react";
import clsx from "clsx";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
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

const CELL_TONE = {
  completed: "bg-status-green-bg text-status-green",
  in_progress: "bg-status-yellow-bg text-status-yellow",
  blocked: "bg-status-red-bg text-status-red",
  not_required: "bg-status-gray-bg text-status-gray",
};

function formatCell(cell, mode) {
  if (cell.status === "not_required" || cell.value === null) return "—";
  if (mode === "foiz") return `${cell.value}%`;
  return cell.value;
}

export default function Tablo() {
  const [mode, setMode] = useState("hajm");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("tablo", tabloSteps), [registerAndAutoStart]);

  async function load(m) {
    setLoading(true);
    const { data } = await adminApi.get("/production/table", { params: { mode: m } });
    setData(data);
    setLoading(false);
  }

  useEffect(() => {
    load(mode);
    const interval = setInterval(() => load(mode), 20000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Real vaqt"
        title="Ishlab chiqarish tablosi"
        subtitle="Buyurtmalar va bosqichlar bo'yicha real vaqtga yaqin holat"
        actions={
          <div data-tutorial="tablo-mode">
            <SegmentedControl
              options={MODES.map((m) => ({ value: m.key, label: m.label }))}
              value={mode}
              onChange={setMode}
            />
          </div>
        }
      />

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
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full text-sm border-collapse min-w-[900px]">
                <thead className="bg-[var(--surface-muted)] text-[var(--ink-soft)] text-xs uppercase tracking-wide sticky top-0">
                  <tr>
                    <th className="text-left font-semibold px-3 py-3 sticky left-0 bg-[var(--surface-muted)]">№</th>
                    <th className="text-left font-semibold px-3 py-3 sticky left-8 bg-[var(--surface-muted)] min-w-[220px]">Buyurtma</th>
                    <th className="text-left font-semibold px-3 py-3">Muddat</th>
                    {data.operations.map((op) => (
                      <th key={op.code} className="text-center font-semibold px-3 py-3 min-w-[100px]">{op.name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)] bg-[var(--surface)]">
                  {data.rows.map((row) => (
                    <tr key={row.order_id} className="hover:bg-[var(--accent-soft)] transition-colors">
                      <td className="px-3 py-3 sticky left-0 bg-[var(--surface)]">{row.index}</td>
                      <td className="px-3 py-3 sticky left-8 bg-[var(--surface)]">
                        <p className="font-semibold">#{row.order_no}</p>
                        <p className="text-xs text-[var(--ink-faint)]">{row.customer_name || row.product_name}</p>
                      </td>
                      <td className="px-3 py-3 text-xs">{row.deadline ? format(new Date(row.deadline), "dd.MM.yyyy") : "—"}</td>
                      {data.operations.map((op) => {
                        const cell = row.cells[op.code];
                        return (
                          <td key={op.code} className="px-3 py-3 text-center">
                            <span className={clsx("inline-block min-w-[56px] px-2 py-1 rounded-md font-semibold text-xs", CELL_TONE[cell.status])}>
                              {formatCell(cell, mode)}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
