import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "./store/authStore";
import AppProviders from "./providers/AppProviders";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminLayout from "./layouts/AdminLayout";

import Login from "./pages/admin/Login";
import Dashboard from "./pages/admin/Dashboard";
import Orders from "./pages/admin/Orders";
import OrderDetail from "./pages/admin/OrderDetail";
import Tablo from "./pages/admin/Tablo";
import Machines from "./pages/admin/Machines";
import Employees from "./pages/admin/Employees";
import Conflicts from "./pages/admin/Conflicts";
import WarehousePage from "./pages/admin/Warehouse";
import Reports from "./pages/admin/Reports";
import Labels from "./pages/admin/Labels";
import NotFound from "./pages/NotFound";

import TerminalLogin from "./pages/terminal/TerminalLogin";
import TerminalLayout from "./layouts/TerminalLayout";
import TerminalScan from "./pages/terminal/TerminalScan";
import TerminalPackaging from "./pages/terminal/TerminalPackaging";
import TerminalWarehouse from "./pages/terminal/TerminalWarehouse";

export default function App() {
  const init = useAuthStore((s) => s.init);
  useEffect(() => {
    init();
  }, [init]);

  return (
    <BrowserRouter>
      <AppProviders>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "rgba(255,255,255,0.85)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            border: "1px solid rgba(211, 216, 227, 0.9)",
            borderRadius: "14px",
            boxShadow: "0 18px 44px rgba(24, 27, 58, 0.16)",
            color: "#0D1017",
            fontSize: "14px",
            fontWeight: 500,
          },
          success: { iconTheme: { primary: "#15803D", secondary: "#FFFFFF" } },
          error: { iconTheme: { primary: "#DC2626", secondary: "#FFFFFF" } },
        }}
      />
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="orders" element={<Orders />} />
          <Route path="orders/:id" element={<OrderDetail />} />
          <Route path="tablo" element={<Tablo />} />
          <Route path="labels" element={<Labels />} />
          <Route path="machines" element={<Machines />} />
          <Route path="employees" element={<Employees />} />
          <Route path="conflicts" element={<Conflicts />} />
          <Route path="warehouse" element={<WarehousePage />} />
          <Route path="reports" element={<Reports />} />
        </Route>

        <Route path="/terminal/login" element={<TerminalLogin />} />
        <Route path="/terminal" element={<TerminalLayout />}>
          <Route index element={<Navigate to="scan" replace />} />
          <Route path="scan" element={<TerminalScan />} />
          <Route path="packaging" element={<TerminalPackaging />} />
          <Route path="warehouse" element={<TerminalWarehouse />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
      </AppProviders>
    </BrowserRouter>
  );
}
