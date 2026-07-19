import { useEffect, useState } from "react";
import { Activity, Boxes, Gauge } from "lucide-react";
import { format } from "date-fns";
import { adminApi } from "../../api/client";
import { toApiInstant } from "../../lib/datetime";
import StatCard from "../../components/ui/StatCard";
import { Card } from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Hero3D from "../../three/Hero3D";
import { PageLoader, EmptyState } from "../../components/ui/Misc";
import DashboardFilters from "../../components/dashboard/DashboardFilters";
import MachineCard from "../../components/dashboard/MachineCard";
import TopPerformers from "../../components/dashboard/TopPerformers";
import { useTutorial } from "../../tutorial/TutorialContext";
import { dashboardSteps } from "../../tutorial/content/dashboard";

const OUTPUT_UNITS = [
  { key: "meter", label: "metr" },
  { key: "piece", label: "dona" },
  { key: "m2", label: "kv.m" },
];

function defaultRange() {
  const now = new Date();
  const workdayStart = new Date(now);
  workdayStart.setHours(7, 0, 0, 0);
  const currentHour = new Date(now);
  currentHour.setMinutes(0, 0, 0);
  return {
    from: format(workdayStart, "yyyy-MM-dd'T'HH:mm"),
    to: format(currentHour, "yyyy-MM-dd'T'HH:mm"),
  };
}

function last4HoursRange() {
  const now = new Date();
  const start = new Date(now.getTime() - 4 * 60 * 60 * 1000);
  return {
    from: format(start, "yyyy-MM-dd'T'HH:mm"),
    to: format(now, "yyyy-MM-dd'T'HH:mm"),
  };
}

function defaultFilters() {
  return {
    ...defaultRange(),
    interval: 15,
    indicator: "volume",
    live: false,
  };
}

function OutputStatCard({ output }) {
  return (
    <Card className="flex h-full items-start gap-4 p-5 transition-shadow duration-300 hover:elevation-lg">
      <div className="rounded-2xl bg-[linear-gradient(135deg,var(--accent-2),var(--accent-2-bright))] p-3 text-white shadow-[0_8px_22px_rgba(71,93,53,0.30)]">
        <Boxes size={22} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-[var(--ink-soft)]">Jami ishlab chiqarish</p>
        <div className="mt-1.5 flex flex-wrap gap-2">
          {OUTPUT_UNITS.map(({ key, label }) => (
            <span key={key} className="inline-flex items-baseline gap-1 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] px-2.5 py-1">
              <span className="font-display text-lg font-semibold text-[var(--ink)]">
                {Number(output[key] ?? 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}
              </span>
              <span className="text-[10px] font-semibold uppercase text-[var(--ink-soft)]">{label}</span>
            </span>
          ))}
        </div>
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const [filters, setFilters] = useState(defaultFilters);
  const [overview, setOverview] = useState(null);
  const [machines, setMachines] = useState([]);
  const [leaders, setLeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("dashboard", dashboardSteps), [registerAndAutoStart]);

  async function load(f) {
    // f.from/f.to are naive <input type="datetime-local"> values (the
    // browser's own local wall clock) — convert to unambiguous UTC instants
    // so the backend never has to guess which timezone they're in.
    const from = toApiInstant(f.from);
    const to = toApiInstant(f.to);
    const params = { from, to, interval: f.interval };
    const [o, m, l] = await Promise.all([
      adminApi.get("/dashboard/overview", { params }),
      adminApi.get("/dashboard/machines", { params }),
      adminApi.get("/dashboard/leaderboard", { params: { from, to } }),
    ]);
    setOverview(o.data);
    setMachines(m.data);
    setLeaders(l.data);
    setLoading(false);
  }

  useEffect(() => {
    load(filters);
    // Also reloads whenever "live" is toggled, since handleFilterChange
    // already swaps from/to to the relevant range before this fires.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.live]);

  useEffect(() => {
    if (!filters.live) return undefined;
    const id = setInterval(() => {
      const range = last4HoursRange();
      load({ ...filters, ...range });
      setFilters((f) => ({ ...f, ...range }));
    }, 15000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.live, filters.interval]);

  function handleFilterChange(patch) {
    setFilters((f) => {
      if (patch.live === true) return { ...f, ...patch, ...last4HoursRange() };
      if (patch.live === false) return { ...f, ...patch, ...defaultRange() };
      return { ...f, ...patch };
    });
  }

  function handleRefresh() {
    load(filters);
  }

  if (loading || !overview) return <PageLoader />;

  return (
    <div className="space-y-6">
      <section className="grain relative overflow-hidden rounded-3xl border border-[var(--border)] elevation-md">
        <Hero3D variant="light" className="opacity-80" />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(105deg,rgba(255,255,255,0.72),rgba(255,255,255,0.25)_55%,transparent)]" />
        <div className="relative z-10 px-6 py-8 sm:px-8 sm:py-10">
          <PageHeader
            eyebrow="Jonli ko'rinish"
            title="Boshqaruv paneli"
            subtitle="Ishlab chiqarish holatining real vaqtdagi umumiy ko'rinishi"
          />
        </div>
      </section>

      <div data-tutorial="dashboard-stats" className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatCard
          index={0}
          icon={Gauge}
          label="O'rtacha samaradorlik (OEE)"
          value={`${overview.oee}%`}
          tone={overview.oee >= 90 ? "green" : overview.oee >= 70 ? "orange" : "red"}
        />
        <OutputStatCard output={overview.output} />
        <StatCard
          index={2}
          icon={Activity}
          label="Aktiv stanoklar"
          value={`${overview.active_machines} / ${overview.total_machines}`}
          tone="blue"
        />
      </div>

      <div data-tutorial="dashboard-filters">
        <DashboardFilters filters={filters} onChange={handleFilterChange} onRefresh={handleRefresh} />
      </div>

      <div data-tutorial="dashboard-machines">
        {machines.length === 0 ? (
          <EmptyState title="Aktiv stanok topilmadi" />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {machines.map((m) => (
              <MachineCard key={m.id} machine={m} from={filters.from} to={filters.to} interval={filters.interval} indicator={filters.indicator} />
            ))}
          </div>
        )}
      </div>

      <div data-tutorial="dashboard-top-performers">
        <TopPerformers rows={leaders} />
      </div>
    </div>
  );
}
