import { useEffect, useMemo, useState } from "react";
import { format, startOfMonth, startOfWeek } from "date-fns";
import toast from "react-hot-toast";
import { ClipboardList, CheckCircle2, Clock, PackagePlus, AlertTriangle, FileSpreadsheet, FileDown, Printer } from "lucide-react";
import { adminApi } from "../../api/client";
import StatCard from "../ui/StatCard";
import Button from "../ui/Button";
import { PageLoader } from "../ui/Misc";
import ReportFilters from "./ReportFilters";
import { CompletionTrendChart, StatusDistributionChart, WorkerCompletionChart } from "./ReportCharts";
import TopBottomWorkers from "./TopBottomWorkers";
import WorkerPerformanceTable from "./WorkerPerformanceTable";
import OverdueOrdersCard from "./OverdueOrdersCard";

function getErrorMessage(error) {
  const data = error.response?.data;
  if (typeof data?.detail === "string") return data.detail;
  return "Xatolik yuz berdi";
}

function computeDateRange(filters) {
  const today = new Date();
  const todayStr = format(today, "yyyy-MM-dd");
  if (filters.preset === "today") return { from: todayStr, to: todayStr };
  if (filters.preset === "week") return { from: format(startOfWeek(today, { weekStartsOn: 1 }), "yyyy-MM-dd"), to: todayStr };
  if (filters.preset === "month") return { from: format(startOfMonth(today), "yyyy-MM-dd"), to: todayStr };
  return { from: filters.from || todayStr, to: filters.to || todayStr };
}

function defaultFilters() {
  return { preset: "today", from: "", to: "", status: "", worker: "", department: "" };
}

export default function OrdersReportPanel() {
  const [filters, setFilters] = useState(defaultFilters);
  const [granularity, setGranularity] = useState("day");
  const [overview, setOverview] = useState(null);
  const [workers, setWorkers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState({ excel: false, pdf: false });

  const range = useMemo(() => computeDateRange(filters), [filters]);

  useEffect(() => {
    adminApi.get("/employees/", { params: { is_active_employee: true } }).then(({ data }) => {
      const results = data.results || data;
      setWorkers(results.filter((u) => u.role === "operator" || u.role === "warehouse"));
    });
    adminApi.get("/tsexes/").then(({ data }) => {
      const results = data.results || data;
      setDepartments(results.filter((t) => t.is_active !== false));
    });
  }, []);

  useEffect(() => {
    setLoading(true);
    adminApi
      .get("/reports/orders/overview", {
        params: {
          from: range.from,
          to: range.to,
          status: filters.status || undefined,
          worker: filters.worker || undefined,
          department: filters.department || undefined,
          granularity,
        },
      })
      .then(({ data }) => setOverview(data))
      .finally(() => setLoading(false));
  }, [range.from, range.to, filters.status, filters.worker, filters.department, granularity]);

  async function handleExport(fileType) {
    setExporting((s) => ({ ...s, [fileType]: true }));
    try {
      const response = await adminApi.get("/reports/orders/export", {
        params: {
          from: range.from,
          to: range.to,
          status: filters.status || undefined,
          worker: filters.worker || undefined,
          department: filters.department || undefined,
          granularity,
          file_type: fileType,
        },
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.download = fileType === "excel" ? "hisobot.xlsx" : "hisobot.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setExporting((s) => ({ ...s, [fileType]: false }));
    }
  }

  if (loading && !overview) return <PageLoader />;

  const summary = overview?.summary || { total: 0, completed: 0, in_progress: 0, new: 0, overdue: 0 };

  return (
    <div className="space-y-6">
      <div className="print:hidden">
        <ReportFilters filters={filters} onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))} workers={workers} departments={departments} />
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2 print:hidden">
        <Button variant="secondary" size="sm" loading={exporting.excel} onClick={() => handleExport("excel")}>
          <FileSpreadsheet size={16} /> Excel
        </Button>
        <Button variant="secondary" size="sm" loading={exporting.pdf} onClick={() => handleExport("pdf")}>
          <FileDown size={16} /> PDF
        </Button>
        <Button variant="ghost" size="sm" onClick={() => window.print()}>
          <Printer size={16} /> Chop etish
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard index={0} icon={ClipboardList} label="Jami buyurtmalar" value={summary.total} tone="accent" />
        <StatCard index={1} icon={CheckCircle2} label="Tugallangan" value={summary.completed} tone="green" />
        <StatCard index={2} icon={Clock} label="Jarayonda" value={summary.in_progress} tone="blue" />
        <StatCard index={3} icon={PackagePlus} label="Yangi" value={summary.new} tone="signal" />
        <StatCard index={4} icon={AlertTriangle} label="Kechikkan" value={summary.overdue} tone="red" />
      </div>

      {overview && (
        <>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <StatusDistributionChart distribution={overview.status_distribution} />
            <CompletionTrendChart series={overview.completion_series} granularity={granularity} onGranularityChange={setGranularity} />
          </div>

          <WorkerCompletionChart workers={overview.worker_performance} />

          <TopBottomWorkers workers={overview.worker_performance} />

          <WorkerPerformanceTable rows={overview.worker_performance} from={range.from} to={range.to} />

          <OverdueOrdersCard orders={overview.overdue_orders} />
        </>
      )}
    </div>
  );
}
