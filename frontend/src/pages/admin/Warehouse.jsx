import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { PageLoader } from "../../components/ui/Misc";
import { StatusBadge } from "../../components/ui/Badge";
import { format } from "date-fns";
import { useTutorial } from "../../tutorial/TutorialContext";
import { warehouseSteps } from "../../tutorial/content/warehouse";

const STATUS_LABELS = { open: "Ochiq", completed: "Yakunlangan", warehouse: "Omborda", delivered: "Topshirildi" };

export default function WarehousePage() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("warehouse", warehouseSteps), [registerAndAutoStart]);

  async function load() {
    setLoading(true);
    const { data } = await adminApi.get("/warehouse/packages");
    setPackages(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function deliver(id) {
    try {
      await adminApi.post("/warehouse/deliver", { package_id: id });
      toast.success("Mijozga topshirildi");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Xatolik");
    }
  }

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Ombor" title="Tayyor ombor" subtitle="Qadoqlar va ularning ombordagi holati" />

      <Card>
        <CardHeader data-tutorial="warehouse-header" title="Qadoqlar" subtitle={`${packages.length} ta qadoq`} />
        <CardBody data-tutorial="warehouse-table" className="p-0">
          <Table>
            <Thead>
              <tr>
                <Th>Qadoq</Th>
                <Th>Buyurtma</Th>
                <Th>Detallar</Th>
                <Th>Yaratilgan</Th>
                <Th>Status</Th>
                <Th></Th>
              </tr>
            </Thead>
            <Tbody>
              {packages.length === 0 && <EmptyRow colSpan={6} />}
              {packages.map((p) => (
                <Tr key={p.id}>
                  <Td className="font-mono text-xs">{p.package_no}</Td>
                  <Td>#{p.order_no}</Td>
                  <Td>{p.items_count}</Td>
                  <Td className="text-xs">{format(new Date(p.created_at), "dd.MM.yyyy HH:mm")}</Td>
                  <Td><StatusBadge status={p.status} labels={STATUS_LABELS} /></Td>
                  <Td>
                    {p.status === "warehouse" && (
                      <Button size="sm" onClick={() => deliver(p.id)}>Mijozga topshirish</Button>
                    )}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </CardBody>
      </Card>
    </div>
  );
}
