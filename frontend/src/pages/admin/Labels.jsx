import { useEffect, useState } from "react";
import { Printer, Search } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { Input, Select, Field } from "../../components/ui/Input";
import { Checkbox } from "../../components/ui/Checkbox";
import { EmptyState } from "../../components/ui/Misc";
import { useTutorial } from "../../tutorial/TutorialContext";
import { labelsSteps } from "../../tutorial/content/labels";

export default function Labels() {
  const [search, setSearch] = useState("");
  const [parts, setParts] = useState([]);
  const [selected, setSelected] = useState([]);
  const [width, setWidth] = useState(70);
  const [height, setHeight] = useState(50);
  const [loading, setLoading] = useState(false);
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("labels", labelsSteps), [registerAndAutoStart]);

  async function find() {
    if (!search) return;
    setLoading(true);
    const { data } = await adminApi.get("/parts/", { params: { search } });
    setParts(data.results || data);
    setSelected([]);
    setLoading(false);
  }

  function toggle(id) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  function selectAll() {
    setSelected(parts.length === selected.length ? [] : parts.map((p) => p.id));
  }

  async function print() {
    if (selected.length === 0) return toast.error("Detal tanlanmagan");
    const res = await adminApi.post(
      "/labels/print",
      { part_ids: selected, width_mm: width, height_mm: height },
      { responseType: "blob" }
    );
    const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    window.open(url, "_blank");
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Chop etish" title="QR / Birka chop etish" subtitle="Buyurtma yoki detal kodi bo'yicha qidirib, birka chop eting" />

      <Card>
        <CardBody data-tutorial="labels-search-card" className="flex flex-wrap items-end gap-3">
          <Field label="Buyurtma raqami yoki detal kodi/nomi" className="w-full sm:w-auto">
            <div className="relative w-full sm:w-72">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-(--ink-soft)" />
              <Input className="pl-8" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && find()} />
            </div>
          </Field>
          <Field label="Kenglik (mm)" className="w-full sm:w-auto">
            <Select value={width} onChange={(e) => setWidth(Number(e.target.value))} className="w-full sm:w-28">
              <option value={58}>58</option>
              <option value={70}>70</option>
              <option value={100}>100</option>
            </Select>
          </Field>
          <Field label="Balandlik (mm)" className="w-full sm:w-auto">
            <Select value={height} onChange={(e) => setHeight(Number(e.target.value))} className="w-full sm:w-28">
              <option value={40}>40</option>
              <option value={50}>50</option>
              <option value={60}>60</option>
            </Select>
          </Field>
          <Button onClick={find} disabled={loading} className="w-full sm:w-auto">Qidirish</Button>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Natijalar"
          subtitle={`${parts.length} ta detal topildi`}
          actions={
            <div data-tutorial="labels-select-print" className="flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" onClick={selectAll} className="w-full sm:w-auto">Barchasini tanlash</Button>
              <Button size="sm" onClick={print} className="w-full sm:w-auto"><Printer size={15} /> Chop etish ({selected.length})</Button>
            </div>
          }
        />
        <CardBody data-tutorial="labels-results" className="p-0">
          {parts.length === 0 ? (
            <EmptyState title="Qidiruv natijasi yo'q" subtitle="Buyurtma raqami yoki detal kodini kiriting" />
          ) : (
            <Table>
              <Thead>
                <tr>
                  <Th></Th>
                  <Th>Kod</Th>
                  <Th>Nomi</Th>
                  <Th>Buyurtma</Th>
                  <Th>O'lcham</Th>
                  <Th>QR token</Th>
                </tr>
              </Thead>
              <Tbody>
                {parts.map((p) => (
                  <Tr key={p.id}>
                    <Td><Checkbox checked={selected.includes(p.id)} onChange={() => toggle(p.id)} /></Td>
                    <Td className="font-mono text-xs">{p.code}</Td>
                    <Td>{p.name}</Td>
                    <Td>#{p.order_no}</Td>
                    <Td>{p.length_mm}x{p.width_mm}x{p.thickness_mm}</Td>
                    <Td className="font-mono text-xs">{p.qr_token}</Td>
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
