import { useEffect, useState } from "react";
import { format } from "date-fns";
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { adminApi } from "../../api/client";
import { toApiInstant } from "../../lib/datetime";
import { Card, CardBody, CardHeader } from "../ui/Card";
import Badge from "../ui/Badge";
import { CHART, tooltipStyle } from "../ui/chartTheme";

export default function MachineCard({ machine, from, to, interval, indicator }) {
  const [series, setSeries] = useState(null);
  const [loadingSeries, setLoadingSeries] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoadingSeries(true);
    adminApi
      .get(`/dashboard/machines/${machine.id}/series`, {
        params: { from: toApiInstant(from), to: toApiInstant(to), interval },
      })
      .then(({ data }) => {
        if (!cancelled) setSeries(data);
      })
      .finally(() => {
        if (!cancelled) setLoadingSeries(false);
      });
    return () => {
      cancelled = true;
    };
  }, [machine.id, from, to, interval]);

  const bucketHours = interval / 60;
  const capacityPerBucket = series?.capacity_per_hour ? Number(series.capacity_per_hour) * bucketHours : null;

  const chartData = (series?.series || []).map((p) => ({
    time: format(new Date(p.t), "HH:mm"),
    value:
      indicator === "efficiency" && capacityPerBucket
        ? Math.round((p.value / capacityPerBucket) * 1000) / 10
        : p.value,
  }));
  const referenceY = indicator === "efficiency" ? (capacityPerBucket ? 100 : null) : capacityPerBucket;

  return (
    <Card className="overflow-hidden">
      <CardHeader
        title={`${machine.operation_code} ${machine.operation_name} - ${machine.unit_label.toUpperCase()}`}
        subtitle={`ID: ${machine.id}`}
        actions={<Badge tone="blue">AKTIV</Badge>}
      />
      <CardBody className="space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--ink-soft)]">Davr ichidagi o'rtacha samaradorlik</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--ink)]">
              {machine.period_efficiency !== null ? `${machine.period_efficiency}%` : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--ink-soft)]">Davr ichidagi hajm</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--ink)]">
              {machine.period_volume} <span className="text-sm font-normal text-[var(--ink-soft)]">{machine.unit_label}</span>
            </p>
          </div>
        </div>

        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-muted)]/40 p-3">
            {loadingSeries || !series ? (
              <div className="flex h-64 items-center justify-center text-sm text-[var(--ink-faint)]">Yuklanmoqda...</div>
            ) : (
              <>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -4, bottom: 0 }}>
                      <defs>
                        <linearGradient id={`area-${machine.id}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={CHART.accent} stopOpacity={0.35} />
                          <stop offset="100%" stopColor={CHART.accent} stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART.grid} />
                      <XAxis dataKey="time" tick={{ fontSize: 11, fill: CHART.axis }} stroke={CHART.grid} />
                      <YAxis width={28} tick={{ fontSize: 11, fill: CHART.axis }} tickMargin={4} stroke={CHART.grid} />
                      <Tooltip {...tooltipStyle} />
                      {referenceY != null && (
                        <ReferenceLine
                          y={referenceY}
                          stroke={CHART.danger}
                          strokeDasharray="4 4"
                          label={{ value: indicator === "efficiency" ? "100%" : "MAX", position: "insideTopRight", fill: CHART.danger, fontSize: 11 }}
                        />
                      )}
                      <Area type="monotone" dataKey="value" stroke={CHART.accent} fill={`url(#area-${machine.id})`} strokeWidth={2.5} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-2 flex items-center justify-between text-xs font-medium text-[var(--ink-soft)]">
                  <span>Quvvat: {series.capacity_per_hour ? `${series.capacity_per_hour} ${series.unit_label}/soat` : "—"}</span>
                  <span>MAX: {series.max_value} {series.unit_label}</span>
                </div>
              </>
            )}
        </div>
      </CardBody>
    </Card>
  );
}
