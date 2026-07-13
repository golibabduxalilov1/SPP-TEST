import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { EmptyState, PageLoader } from "../../components/ui/Misc";
import Badge, { StatusBadge } from "../../components/ui/Badge";
import SegmentedControl from "../../components/ui/SegmentedControl";
import { format } from "date-fns";
import { useTutorial } from "../../tutorial/TutorialContext";
import { conflictsSteps } from "../../tutorial/content/conflicts";

const FILTER_OPTIONS = [
  { value: "pending", label: "Kutilmoqda" },
  { value: "resolved", label: "Hal qilingan" },
  { value: "", label: "Barchasi" },
];

const REASON_LABELS = {
  invalid_qr: "QR topilmadi", wrong_operation: "Noto'g'ri bosqich", previous_not_completed: "Oldingi bosqich tugamagan",
  duplicate_scan: "Qayta skan", order_closed: "Buyurtma yopilgan", device_not_allowed: "Qurilma ruxsatsiz",
  review_required: "Tekshirish talab qilinadi",
};

export default function Conflicts() {
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("pending");
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("conflicts", conflictsSteps), [registerAndAutoStart]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const { data } = await adminApi.get("/conflicts/", { params: { status: filter || undefined } });
      setConflicts(data.results || data);
    } catch (err) {
      setConflicts([]);
      setError(err.response?.status === 403 ? "forbidden" : "load_failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function resolve(id, resolution) {
    try {
      await adminApi.post(`/conflicts/${id}/resolve/`, { resolution });
      toast.success("Konflikt hal qilindi");
      load();
    } catch {
      toast.error("Xatolik yuz berdi");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Nazorat"
        title="Konfliktlar"
        subtitle="Server rad qilgan yoki tekshirish talab qiladigan skanlar"
        actions={
          <div data-tutorial="conflicts-filter">
            <SegmentedControl options={FILTER_OPTIONS} value={filter} onChange={setFilter} />
          </div>
        }
      />

      <Card>
        <CardHeader title="Ro'yxat" subtitle={`${conflicts.length} ta konflikt`} />
        <CardBody data-tutorial="conflicts-table" className="p-0">
          {loading ? (
            <PageLoader />
          ) : error === "forbidden" ? (
            <EmptyState
              title="Ruxsat yo'q"
              subtitle="Konfliktlarni ko'rish va hal qilish uchun master yoki boshqaruv roli kerak."
            />
          ) : error ? (
            <EmptyState
              title="Konfliktlar yuklanmadi"
              subtitle="Server bilan aloqa vaqtida xatolik yuz berdi. Sahifani yangilab ko'ring."
            />
          ) : (
            <Table>
              <Thead>
                <tr>
                  <Th>Vaqt</Th>
                  <Th>Detal</Th>
                  <Th>Buyurtma</Th>
                  <Th>Bosqich</Th>
                  <Th>Usta</Th>
                  <Th>Sabab</Th>
                  <Th>Status</Th>
                  <Th></Th>
                </tr>
              </Thead>
              <Tbody>
                {conflicts.length === 0 && <EmptyRow colSpan={8} />}
                {conflicts.map((c) => (
                  <Tr key={c.id}>
                    <Td className="text-xs">{format(new Date(c.created_at), "dd.MM HH:mm:ss")}</Td>
                    <Td className="font-mono text-xs">{c.scan?.part_code || c.scan?.qr_token}</Td>
                    <Td>#{c.scan?.order_no || "—"}</Td>
                    <Td>{c.scan?.operation_name || "—"}</Td>
                    <Td>{c.scan?.employee_name || "—"}</Td>
                    <Td><Badge tone="red">{REASON_LABELS[c.reason_code] || c.reason_code}</Badge></Td>
                    <Td><StatusBadge status={c.status} labels={{ pending: "Kutilmoqda", resolved: "Hal qilingan" }} /></Td>
                    <Td>
                      {c.status === "pending" && (
                        <div className="flex gap-1.5">
                          <Button size="sm" variant="success" onClick={() => resolve(c.id, "accepted")}>Qabul qilish</Button>
                          <Button size="sm" variant="danger" onClick={() => resolve(c.id, "rejected")}>Rad etish</Button>
                        </div>
                      )}
                    </Td>
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
