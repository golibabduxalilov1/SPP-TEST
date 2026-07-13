import { useEffect, useState } from "react";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import PageHeader from "../../components/ui/PageHeader";
import { PageLoader } from "../../components/ui/Misc";
import SegmentedControl from "../../components/ui/SegmentedControl";
import { useTutorial } from "../../tutorial/TutorialContext";
import { reportsSteps } from "../../tutorial/content/reports";

const TABS = [
  { key: "production", label: "Ishlab chiqarish", url: "/reports/production", cols: ["operation", "completed", "total", "percent"] },
  { key: "orders", label: "Buyurtmalar", url: "/reports/orders", cols: ["status", "count"] },
  { key: "machines", label: "Stanoklar", url: "/reports/machines", cols: ["machine_id", "name", "status", "scan_count"] },
  { key: "scans", label: "Skanlar", url: "/reports/scans", cols: ["status", "count"] },
  { key: "warehouse", label: "Tayyor ombor", url: "/reports/warehouse", cols: ["status", "count"] },
];

export default function Reports() {
  const [tab, setTab] = useState("production");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const active = TABS.find((t) => t.key === tab);
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("reports", reportsSteps), [registerAndAutoStart]);

  async function load() {
    setLoading(true);
    const { data } = await adminApi.get(active.url);
    setRows(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Analitika" title="Hisobotlar" subtitle="Ishlab chiqarish, buyurtmalar, stanoklar va ombor bo'yicha statistika" />

      <div data-tutorial="reports-tabs">
        <SegmentedControl
          options={TABS.map((t) => ({ value: t.key, label: t.label }))}
          value={tab}
          onChange={setTab}
        />
      </div>

      <Card>
        <CardHeader title={active.label} />
        <CardBody data-tutorial="reports-table" className="p-0">
          {loading ? (
            <PageLoader />
          ) : (
            <Table>
              <Thead>
                <tr>
                  {active.cols.map((c) => <Th key={c}>{c}</Th>)}
                </tr>
              </Thead>
              <Tbody>
                {rows.length === 0 && <EmptyRow colSpan={active.cols.length} />}
                {rows.map((row, i) => (
                  <Tr key={i}>
                    {active.cols.map((c) => (
                      <Td key={c}>{c === "percent" && row[c] !== undefined ? `${row[c]}%` : String(row[c] ?? "—")}</Td>
                    ))}
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
