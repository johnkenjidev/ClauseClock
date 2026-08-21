import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";
import Auth from "@/pages/Auth";
import Dashboard from "@/pages/Dashboard";
import Contracts from "@/pages/Contracts";
import ContractDetail from "@/pages/ContractDetail";
import FindingDetail from "@/pages/FindingDetail";
import ActionCenter from "@/pages/ActionCenter";
import Upload from "@/pages/Upload";
import Accuracy from "@/pages/Accuracy";
import Demo from "@/pages/Demo";
import DemoContracts from "@/pages/DemoContracts";
import DemoContractDetail from "@/pages/DemoContractDetail";
import DemoActionCenter from "@/pages/DemoActionCenter";
import Home from "@/pages/Home";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Auth */}
          <Route path="/login" element={<Auth mode="login" />} />
          <Route path="/signup" element={<Auth mode="signup" />} />

          {/* /app — authenticated workspace */}
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="contracts" element={<Contracts />} />
            <Route path="contracts/:contractId" element={<ContractDetail />} />
            <Route path="findings/:findingId" element={<FindingDetail />} />
            <Route path="actions" element={<ActionCenter />} />
            <Route path="upload" element={<Upload />} />
          </Route>

          {/* /demo — no auth, read-only synthetic workspace */}
          <Route path="/demo" element={<AppShell demo />}>
            <Route index element={<Demo />} />
            <Route path="contracts" element={<DemoContracts />} />
            <Route path="contracts/:contractId" element={<DemoContractDetail />} />
            <Route path="actions" element={<DemoActionCenter />} />
          </Route>

          {/* /accuracy — internal operator instrumentation */}
          <Route path="/accuracy" element={<Accuracy />} />

          <Route path="/" element={<Home />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
