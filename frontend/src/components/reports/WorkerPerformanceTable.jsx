import { Fragment, useEffect, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { format } from "date-fns";
import { adminApi } from "../../api/client";
import { Card, CardHeader, CardBody } from "../ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../ui/Table";
import Badge from "../ui/Badge";
import { EmptyState, Spinner } from "../ui/Misc";

function formatDate(value) {
  return value ? format(new Date(value), "dd.MM.yyyy") : "—";
}

function CompletedOrdersPanel({ workerId, from, to }) {
  const [orders, setOrders] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    adminApi
      .get(`/reports/orders/workers/${workerId}/completed`, { params: { from, to } })
      .then(({ data }) => cancelled! && setOrders(data))
      .catch(() => cancelled! && setOrders([]))
      .finally(() => cancelled! && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [workerId, from, to]);

  if (loading) {
    return (
      <div className="flex items-center gap-2.5 px-4 py-6 text-sm text-(--ink-soft)">
        <Spinner size={16} /> Yuklanmoqda...
      </div>
    );
  }

  if (!orders || orders.length === 0) {
    return <EmptyState title="Tugallangan buyurtma yo'q" subtitle="Tanlangan davrda bu ishchi hech qanday buyurtmani tugallamagan." />;
  }

  return (
    <div className="p-2 sm:p-3">
      <Table label="Tugallangan buyurtmalar">
        <Thead>
          <tr>
            <Th>Buyurtma</Th>
            <Th>Mijoz / obyekt</Th>
            <Th>Ish turi</Th>
            <Th>Yaratilgan</Th>
            <Th>Tugallangan</Th>
            <Th>Status</Th>
          </tr>
        </Thead>
        <Tbody>
          {orders.map((o) => (
            <Tr key={o.id}>
              <Td className="font-medium">#{o.order_no}</Td>
              <Td>{o.customer_name}</Td>
              <Td>{o.work_type}</Td>
              <Td>{formatDate(o.created_at)}</Td>
              <Td>{formatDate(o.completed_at)}</Td>
              <Td><Badge tone="green">{o.status_label}</Badge></Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </div>
  );
}

export default function WorkerPerformanceTable({ rows, from, to }) {
  const [expandedId, setExpandedId] = useState(null);

  function toggle(id) {
    setExpandedId((current) => (current === id ? null : id));
  }

  return (
    <Card>
      <CardHeader title="Ishchilar samaradorligi" subtitle="Har bir ishchining tugatgan va jarayondagi buyurtmalari" />
      <CardBody className="p-0">
        {rows.length === 0 ? (
          <EmptyState title="Ishchi topilmadi" subtitle="Tanlangan filtrlar bo'yicha ishchi ma'lumoti mavjud emas." />
        ) : (
          <Table>
            <Thead>
              <tr>
                <Th className="w-8" />
                <Th>Ishchi F.I.Sh.</Th>
                <Th>Tugatgan buyurtmalar</Th>
                <Th>Jarayondagi buyurtmalar</Th>
                <Th>Oxirgi tugatgan buyurtma</Th>
                <Th className="text-right">Batafsil</Th>
              </tr>
            </Thead>
            <Tbody>
              {rows.length === 0 && <EmptyRow colSpan={6} />}
              {rows.map((row) => {
                const isOpen = expandedId === row.id;
                return (
                  <Fragment key={row.id}>
                    <Tr
                      className="cursor-pointer"
                      onClick={() => toggle(row.id)}
                      aria-expanded={isOpen}
                    >
                      <Td className="text-(--ink-faint)">
                        {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </Td>
                      <Td>
                        <p className="font-medium">{row.name}</p>
                        <p className="text-xs text-(--ink-faint)">{row.role}</p>
                      </Td>
                      <Td><span className="font-semibold">{row.completed_count}</span></Td>
                      <Td>{row.in_progress_count}</Td>
                      <Td>{formatDate(row.last_completed_at)}</Td>
                      <Td className="text-right">
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); toggle(row.id); }}
                          className="focus-ring rounded-lg border border-(--border-strong) px-3 py-1.5 text-xs font-semibold text-(--accent-strong) hover:bg-(--accent-soft)"
                        >
                          {isOpen ? "Yopish" : "Batafsil ko'rish"}
                        </button>
                      </Td>
                    </Tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={6} className="border-t border-(--border-subtle) bg-(--surface-muted) p-0">
                          <CompletedOrdersPanel workerId={row.id} from={from} to={to} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </Tbody>
          </Table>
        )}
      </CardBody>
    </Card>
  );
}
