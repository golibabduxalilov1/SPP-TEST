import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { PageLoader } from "./ui/Misc";

export default function ProtectedRoute({ children }) {
  const { user, ready } = useAuthStore();
  if (!ready) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}
