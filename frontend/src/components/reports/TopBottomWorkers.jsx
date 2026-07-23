import { TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardHeader, CardBody } from "../ui/Card";
import { EmptyState } from "../ui/Misc";

function WorkerList({ rows, emptyLabel }) {
  if (rows.length === 0) {
    return <EmptyState title={emptyLabel} />;
  }
  return (
    <ul className="divide-y divide-(--border-subtle)">
      {rows.map((row, i) => (
        <li key={row.id} className="flex items-center justify-between gap-3 py-2.5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-(--surface-muted) text-xs font-semibold text-(--ink-soft)">
              {i + 1}
            </span>
            <div>
              <p className="text-sm font-medium text-(--ink)">{row.name}</p>
              <p className="text-xs text-(--ink-faint)">{row.role}</p>
            </div>
          </div>
          <span className="font-display text-lg font-semibold text-(--ink) tabular">{row.completed_count}</span>
        </li>
      ))}
    </ul>
  );
}

export default function TopBottomWorkers({ workers }) {
  const withActivity = workers.filter((w) => w.completed_count > 0);
  const top = [...withActivity].sort((a, b) => b.completed_count - a.completed_count).slice(0, 5);
  const bottom = [...workers].sort((a, b) => a.completed_count - b.completed_count).slice(0, 5);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader
          title="Eng ko'p tugatgan ishchilar"
          actions={<TrendingUp size={18} className="text-status-green" />}
        />
        <CardBody>
          <WorkerList rows={top} emptyLabel="Hozircha hech kim buyurtma tugatmagan" />
        </CardBody>
      </Card>
      <Card>
        <CardHeader
          title="Eng kam tugatgan ishchilar"
          actions={<TrendingDown size={18} className="text-status-red" />}
        />
        <CardBody>
          <WorkerList rows={bottom} emptyLabel="Ishchi ma'lumoti mavjud emas" />
        </CardBody>
      </Card>
    </div>
  );
}
