// /demo/contracts/:id — read-only synthetic contract detail.
import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Eyebrow } from "@/components/cc/Primitives";
import { FindingCard } from "@/components/cc/FindingCard";
import { buildDemoWorkspace } from "@/data/demoWorkspace";

const money = (v, cur) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: cur || "USD", maximumFractionDigits: 0 }).format(v);

export default function DemoContractDetail() {
  const { contractId } = useParams();
  const navigate = useNavigate();
  const { contracts } = useMemo(() => buildDemoWorkspace(new Date()), []);
  const contract = contracts.find((c) => c.id === contractId);

  if (!contract) return <p className="cc-plain-english">Contract not found in the demo.</p>;

  return (
    <div data-testid="demo-contract-detail" className="max-w-3xl">
      <button onClick={() => navigate("/demo/contracts")}
        className="cc-eyebrow text-ink-soft hover:text-ink flex items-center gap-1.5 mb-6">
        <ArrowLeft className="h-4 w-4" /> Demo contracts
      </button>

      <Eyebrow>Contract · synthetic</Eyebrow>
      <h1 className="cc-finding-title text-2xl mt-2">{contract.name}</h1>
      <p className="cc-days-remaining mt-1">
        {contract.counterparty} · <span className="cc-money">{money(contract.annual_value, contract.currency)}</span> · Source: synthetic demo data
      </p>

      <div className="mt-8">
        <Eyebrow>What matters</Eyebrow>
        <div className="cc-seal-rule mt-4 mb-5" />
        <div className="space-y-6">
          {contract.findings.map((f) => <FindingCard key={f.id} finding={f} readOnly />)}
        </div>
      </div>
    </div>
  );
}
