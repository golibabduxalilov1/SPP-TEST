import { Card, CardBody } from "../ui/Card";
import { Field, Input, Select } from "../ui/Input";
import SegmentedControl from "../ui/SegmentedControl";

const RANGE_OPTIONS = [
  { value: "today", label: "Bugun" },
  { value: "week", label: "Hafta" },
  { value: "month", label: "Oy" },
  { value: "custom", label: "Ixtiyoriy" },
];

export default function ReportFilters({ filters, onChange, workers, departments }) {
  return (
    <Card>
      <CardBody className="flex flex-wrap items-end gap-4">
        <div>
          <Field label="Davr">
            <SegmentedControl options={RANGE_OPTIONS} value={filters.preset} onChange={(preset) => onChange({ preset })} />
          </Field>
        </div>

        {filters.preset === "custom" && (
          <>
            <div className="w-full sm:w-44">
              <Field label="Boshlanish">
                <Input type="date" value={filters.from} onChange={(e) => onChange({ from: e.target.value })} />
              </Field>
            </div>
            <div className="w-full sm:w-44">
              <Field label="Tugash">
                <Input type="date" value={filters.to} onChange={(e) => onChange({ to: e.target.value })} />
              </Field>
            </div>
          </>
        )}

        <div className="w-full sm:w-52">
          <Field label="Buyurtma holati">
            <Select value={filters.status} onChange={(e) => onChange({ status: e.target.value })}>
              <option value="">Barcha holatlar</option>
              <option value="new">Yangi</option>
              <option value="in_progress">Jarayonda</option>
              <option value="completed">Tugallangan</option>
              <option value="cancelled">Bekor qilingan</option>
            </Select>
          </Field>
        </div>

        <div className="w-full sm:w-56">
          <Field label="Ishchi">
            <Select value={filters.worker} onChange={(e) => onChange({ worker: e.target.value })}>
              <option value="">Barcha ishchilar</option>
              {workers.map((w) => (
                <option key={w.id} value={w.id}>{w.first_name || w.username} {w.last_name}</option>
              ))}
            </Select>
          </Field>
        </div>

        {departments.length > 0 && (
          <div className="w-full sm:w-52">
            <Field label="Bo'lim / hudud">
              <Select value={filters.department} onChange={(e) => onChange({ department: e.target.value })}>
                <option value="">Barcha bo'limlar</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </Select>
            </Field>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
