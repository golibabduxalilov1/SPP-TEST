import { RefreshCw } from "lucide-react";
import { Card, CardBody } from "../ui/Card";
import { Field, Input, Select } from "../ui/Input";
import Button from "../ui/Button";
import Toggle from "../ui/Toggle";

const INTERVALS = [5, 15, 30, 60];

export default function DashboardFilters({ filters, onChange, onRefresh }) {
  return (
    <Card>
      <CardBody className="flex flex-wrap items-end gap-4">
        <div className="w-56">
          <Field label="Boshlanish">
            <Input type="datetime-local" value={filters.from} onChange={(e) => onChange({ from: e.target.value })} />
          </Field>
        </div>
        <div className="w-56">
          <Field label="Tugash">
            <Input type="datetime-local" value={filters.to} onChange={(e) => onChange({ to: e.target.value })} />
          </Field>
        </div>
        <div className="w-36">
          <Field label="Interval">
            <Select value={filters.interval} onChange={(e) => onChange({ interval: Number(e.target.value) })}>
              {INTERVALS.map((m) => (
                <option key={m} value={m}>{m} daqiqa</option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="w-40">
          <Field label="Ko'rsatkich">
            <Select value={filters.indicator} onChange={(e) => onChange({ indicator: e.target.value })}>
              <option value="volume">Miqdor</option>
              <option value="efficiency">Samaradorlik</option>
            </Select>
          </Field>
        </div>
        <div className="pb-2.5">
          <Toggle
            label="Live rejim"
            checked={filters.live}
            onChange={(e) => onChange({ live: e.target.checked })}
          />
        </div>
        <Button type="button" onClick={onRefresh} className="ml-auto">
          <RefreshCw size={15} /> Yangilash
        </Button>
      </CardBody>
    </Card>
  );
}
