import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import Dashboard from "@/pages/Dashboard";
import Contracts from "@/pages/Contracts";
import ContractDetail from "@/pages/ContractDetail";
import FindingDetail from "@/pages/FindingDetail";
import ActionCenter from "@/pages/ActionCenter";
import Upload from "@/pages/Upload";
import Accuracy from "@/pages/Accuracy";
import Demo from "@/pages/Demo";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* /app — authenticated workspace shell */}
        <Route path="/app" element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="contracts" element={<Contracts />} />
          <Route path="contracts/:contractId" element={<ContractDetail />} />
          <Route path="findings/:findingId" element={<FindingDetail />} />
          <Route path="actions" element={<ActionCenter />} />
          <Route path="upload" element={<Upload />} />
        </Route>

        {/* /demo — no auth, read-only synthetic workspace shell (PART 5.9) */}
        <Route path="/demo" element={<AppShell demo />}>
          <Route index element={<Demo />} />
          <Route path="contracts" element={<Contracts />} />
          <Route path="actions" element={<ActionCenter />} />
        </Route>

        {/* /accuracy — internal operator instrumentation */}
        <Route path="/accuracy" element={<Accuracy />} />

        <Route path="/" element={<Navigate to="/app" replace />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
