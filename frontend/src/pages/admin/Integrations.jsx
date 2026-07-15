import { useCallback, useEffect, useState } from "react";
import { Plug, RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import { adminApi } from "../../api/client";
import { Card, CardHeader, CardBody } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import PageHeader from "../../components/ui/PageHeader";
import { PageLoader } from "../../components/ui/Misc";
import { StatusBadge } from "../../components/ui/Badge";

const STATUS_LABELS = { success: "Muvaffaqiyatli", failed: "Muvaffaqiyatsiz" };

function formatDateTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("uz-UZ");
}

export default function Integrations() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const { data } = await adminApi.get("/integrations/odoo/health/");
      setHealth(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [load]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Integratsiyalar"
        title="Odoo sinxronizatsiyasi"
        subtitle="Odoo Cloud'dan tasdiqlangan buyurtmalarni bir tomonlama (read-only) o'qib olish holati"
      />

      {loading || !health ? (
        <PageLoader />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardBody className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--ink-faint)]">Holat</p>
                  <p className="mt-1 text-lg font-semibold text-[var(--ink)]">
                    {health.sync_enabled ? "Yoqilgan" : "O'chirilgan"}
                  </p>
                </div>
                <Plug size={20} className="text-[var(--accent-strong)]" />
              </CardBody>
            </Card>
            <Card>
              <CardBody className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--ink-faint)]">Odoo ulanishi</p>
                  <p className="mt-1 text-lg font-semibold text-[var(--ink)]">
                    {health.connection_ok ? "Ulangan" : "Ulanmagan"}
                  </p>
                </div>
                {health.connection_ok ? (
                  <CheckCircle2 size={20} className="text-status-green" />
                ) : (
                  <XCircle size={20} className="text-status-red" />
                )}
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--ink-faint)]">Oxirgi muvaffaqiyatli sync</p>
                <p className="mt-1 text-sm font-semibold text-[var(--ink)]">{formatDateTime(health.last_success_at)}</p>
              </CardBody>
            </Card>
            <Card>
              <CardBody className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--ink-faint)]">Keyingi sync</p>
                  <p className="mt-1 text-sm font-semibold text-[var(--ink)]">
                    {health.next_sync_in_seconds != null ? `~${health.next_sync_in_seconds}s` : "—"}
                    <span className="ml-1 font-normal text-[var(--ink-faint)]">/ har {health.interval_seconds}s</span>
                  </p>
                </div>
                <RefreshCw size={20} className="text-[var(--ink-faint)]" />
              </CardBody>
            </Card>
          </div>

          <Card>
            <CardHeader title="Oxirgi 10 ta sync urinishi" />
            <CardBody className="p-0">
              <Table>
                <Thead>
                  <tr>
                    <Th>Vaqt</Th>
                    <Th>Holat</Th>
                    <Th>Import qilingan buyurtmalar</Th>
                    <Th>Xatolik</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {health.recent_logs.length === 0 && <EmptyRow colSpan={4} message="Hali sinxronizatsiya bo'lmagan" />}
                  {health.recent_logs.map((log) => (
                    <Tr key={log.id}>
                      <Td>{formatDateTime(log.timestamp)}</Td>
                      <Td><StatusBadge status={log.status} labels={STATUS_LABELS} /></Td>
                      <Td>{log.orders_imported_count}</Td>
                      <Td className="max-w-xs truncate text-[var(--ink-soft)]" title={log.error_message}>
                        {log.error_message || "—"}
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}
