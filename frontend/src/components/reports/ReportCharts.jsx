import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { format, parseISO } from "date-fns";
import { Card, CardHeader, CardBody } from "../ui/Card";
import SegmentedControl from "../ui/SegmentedControl";
import { EmptyState } from "../ui/Misc";
import { CHART, tooltipStyle } from "../ui/chartTheme";

const GRANULARITY_OPTIONS = [
  { value: "day", label: "Kunlik" },
  { value: "week", label: "Haftalik" },
  { value: "month", label: "Oylik" },
];

const STATUS_COLORS = {
  new: CHART.signal,
  in_progress: CHART.accentBright,
  completed: "#4E7D4F",
  cancelled: CHART.danger,
};

function formatPeriodLabel(period, granularity) {
  if (granularity === "month") {
    const [year, month] = period.split("-");
    return format(new Date(Number(year), Number(month) - 1, 1), "MMM yyyy");
  }
  return format(parseISO(period), "dd.MM");
}

export function CompletionTrendChart({ series, granularity, onGranularityChange }) {
  const data = series.map((point) => ({ ...point, label: formatPeriodLabel(point.period, granularity) }));

  return (
    <Card>
      <CardHeader
        title="Tugallangan buyurtmalar dinamikasi"
        subtitle="Vaqt bo'yicha tugallangan buyurtmalar soni"
        actions={<SegmentedControl options={GRANULARITY_OPTIONS} value={granularity} onChange={onGranularityChange} />}
      />
      <CardBody>
        {data.length === 0 ? (
          <EmptyState title="Ma'lumot yo'q" subtitle="Tanlangan davrda tugallangan buyurtma topilmadi." />
        ) : (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: CHART.axis }} axisLine={{ stroke: CHART.grid }} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: CHART.axis }} axisLine={false} tickLine={false} width={30} />
                <Tooltip {...tooltipStyle} formatter={(value) => [value, "Tugallangan"]} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} fill={CHART.accent} maxBarSize={38} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export function StatusDistributionChart({ distribution }) {
  const data = distribution.filter((d) => d.count > 0);
  const total = distribution.reduce((sum, d) => sum + d.count, 0);

  return (
    <Card>
      <CardHeader title="Buyurtma statuslari taqsimoti" subtitle="Tanlangan davrdagi buyurtmalarning holat bo'yicha ulushi" />
      <CardBody>
        {total === 0 ? (
          <EmptyState title="Ma'lumot yo'q" subtitle="Tanlangan davrda buyurtma topilmadi." />
        ) : (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="count" nameKey="label" innerRadius={62} outerRadius={92} paddingAngle={2}>
                  {data.map((entry) => (
                    <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || CHART.series[0]} />
                  ))}
                </Pie>
                <Tooltip {...tooltipStyle} formatter={(value, name) => [value, name]} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: "var(--ink-soft)" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export function WorkerCompletionChart({ workers }) {
  const data = workers
    .filter((w) => w.completed_count > 0)
    .slice(0, 10)
    .map((w) => ({ name: w.name, count: w.completed_count }));

  return (
    <Card>
      <CardHeader title="Ishchilar kesimida tugallangan buyurtmalar" subtitle="Har bir ishchi tugatgan buyurtmalar soni" />
      <CardBody>
        {data.length === 0 ? (
          <EmptyState title="Ma'lumot yo'q" subtitle="Tanlangan davrda hech kim buyurtma tugatmagan." />
        ) : (
          <div className="w-full" style={{ height: Math.max(180, data.length * 42) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: CHART.axis }} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={130}
                  tick={{ fontSize: 12, fill: "var(--ink)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip {...tooltipStyle} formatter={(value) => [value, "Tugallangan"]} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} fill={CHART.signal} maxBarSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
