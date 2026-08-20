import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export function ProtectedRoute({ children }) {
  const { user } = useAuth();
  if (user === null)
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <p className="cc-days-remaining">Loading…</p>
      </div>
    );
  if (user === false) return <Navigate to="/login" replace />;
  return children;
}
