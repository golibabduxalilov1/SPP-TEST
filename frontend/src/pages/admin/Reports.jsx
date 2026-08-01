import { useEffect, useState } from "react";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import PageHeader from "../../components/ui/PageHeader";
import { PageLoader } from "../../components/ui/Misc";
import SegmentedControl from "../../components/ui/SegmentedControl";
import OrdersReportPanel from "../../components/reports/OrdersReportPanel";

const TABS = [
  { key: "orders", label: "Buyurtmalar" },
  { key: "production", label: "Ishlab chiqarish", url: "/reports/production", cols: ["operation", "unit_label", "completed", "total", "percent"] },
  { key: "machines", label: "Dastgohlar", url: "/reports/machines", cols: ["machine_id", "name", "status", "scan_count"] },
  { key: "scans", label: "Skanlar", url: "/reports/scans", cols: ["status", "count"] },
  { key: "warehouse", label: "Tayyor ombor", url: "/reports/warehouse", cols: ["status", "count"] },
];

const COLUMN_LABELS = {
  operation: "Bosqich",
  unit_label: "Birlik",
  completed: "Bajarilgan",
  total: "Jami",
  percent: "Foiz",
  status: "Holat",
  count: "Soni",
  machine_id: "Dastgoh ID",
  name: "Nomi",
  scan_count: "Skanlar soni",
};

const STATUS_LABELS = {
  pending: "Kutilmoqda",
  in_progress: "Jarayonda",
  completed: "Bajarilgan",
  blocked: "Bloklangan",
  active: "Faol",
  inactive: "Nofaol",
  maintenance: "Ta'mirda",
  broken: "Buzilgan",
  accepted: "Qabul qilingan",
  rejected: "Rad etilgan",
  resolved: "Hal qilingan",
  warehouse: "Omborda",
  delivered: "Topshirilgan",
  cancelled: "Bekor qilingan",
};

export default function Reports() {
  const [tab, setTab] = useState("orders");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const active = TABS.find((t) => t.key === tab);

  async function load() {
    if (!active.url) return;
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
      <PageHeader
        eyebrow="Analitika"
        title="Hisobotlar"
        subtitle="Buyurtmalar, ishchilar samaradorligi, ishlab chiqarish va ombor bo'yicha statistika"
        className="print:hidden"
      />

      <div data-tutorial="reports-tabs" className="print:hidden">
        <SegmentedControl
          options={TABS.map((t) => ({ value: t.key, label: t.label }))}
          value={tab}
          onChange={setTab}
        />
      </div>

      {tab === "orders" ? (
        <div data-tutorial="reports-table">
          <OrdersReportPanel />
        </div>
      ) : (
        <Card>
          <CardHeader title={active.label} />
          <CardBody data-tutorial="reports-table" className="p-0">
            {loading ? (
              <PageLoader />
            ) : (
              <Table>
                <Thead>
                  <tr>
                    {active.cols.map((c) => <Th key={c}>{COLUMN_LABELS[c] || c}</Th>)}
                  </tr>
                </Thead>
                <Tbody>
                  {rows.length === 0 && <EmptyRow colSpan={active.cols.length} />}
                  {rows.map((row, i) => (
                    <Tr key={i}>
                      {active.cols.map((c) => (
                        <Td key={c}>
                          {c === "percent" && row[c] !== undefined
                            ? `${row[c]}%`
                            : c === "status"
                            ? STATUS_LABELS[row[c]] || String(row[c] ?? "—")
                            : String(row[c] ?? "—")}
                        </Td>
                      ))}
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}
