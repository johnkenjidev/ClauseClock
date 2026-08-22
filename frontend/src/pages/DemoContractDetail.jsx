// /demo/contracts/:id — read-only synthetic contract detail (Stage 5).
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, FileText } from "lucide-react";
import { Eyebrow } from "@/components/cc/Primitives";
import { FindingCard } from "@/components/cc/FindingCard";
import { buildDemoWorkspace } from "@/data/demoWorkspace";
import { cn } from "@/lib/utils";

const money = (v, cur) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: cur || "USD", maximumFractionDigits: 0 }).format(v);

const PURPOSE_LABEL = {
  effective_date: "Effective date",
  renewal_term: "Renewal term",
  notice_period: "Notice period",
  notice_method: "Notice method",
  notice_recipient: "Notice recipient",
  business_day_definition: "Business day definition",
  deemed_receipt: "Deemed receipt",
  notice_anchor: "Notice anchor",
  notice_anchor_prior: "Notice anchor — prior extraction (not applied)",
  value: "Contract value",
  increase: "Price increase",
  objection: "Objection window",
  increase_basis: "What it applies to",
  termination_right: "Termination right",
  effective_timing: "Effective timing",
  termination_fee: "Termination fee",
  obligation: "Clause",
  window: "Timing window",
  amount: "Amount",
  party: "Who it applies to",
  method: "Method",
};

export default function DemoContractDetail() {
  const { contractId } = useParams();
  const navigate = useNavigate();
  const { contracts } = useMemo(() => buildDemoWorkspace(new Date()), []);
  const contract = contracts.find((c) => c.id === contractId);

  // Initialize selected finding to the first finding
  const [selectedFindingId, setSelectedFindingId] = useState(contract?.findings[0]?.id || "");

  if (!contract) return <p className="cc-plain-english">Contract not found in the demo.</p>;

  const activeFinding = contract.findings.find((f) => f.id === selectedFindingId) || contract.findings[0];

  return (
    <div data-testid="demo-contract-detail" className="max-w-6xl w-full mx-auto">
      <button onClick={() => navigate("/demo")}
        className="cc-eyebrow text-ink-soft hover:text-ink flex items-center gap-1.5 mb-6 group transition-colors">
        <ArrowLeft className="h-4 w-4 group-hover:-translate-x-0.5 transition-transform" /> Demo overview
      </button>

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-rule pb-6">
        <div>
          <Eyebrow>Contract · synthetic</Eyebrow>
          <h1 className="cc-finding-title text-2xl sm:text-3xl mt-2 font-archivo font-bold tracking-tight text-ink">{contract.name}</h1>
          <p className="cc-days-remaining mt-1">
            {contract.counterparty} · <span className="cc-money">{money(contract.annual_value, contract.currency)}</span> · Source: entered by you
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-8 items-start">
        {/* Left Column: Calm Summary Panel */}
        <div className="lg:col-span-7 space-y-6">
          <div>
            <Eyebrow>What matters — renewals & findings</Eyebrow>
            <div className="cc-seal-rule mt-4 mb-5" />
          </div>

          <div className="space-y-6">
            {contract.findings.map((f) => (
              <div
                key={f.id}
                onClick={() => setSelectedFindingId(f.id)}
                className={cn(
                  "cursor-pointer rounded-lg transition-all duration-200",
                  selectedFindingId === f.id
                    ? "ring-2 ring-seal ring-offset-2 ring-offset-paper"
                    : "opacity-85 hover:opacity-100"
                )}
              >
                <FindingCard finding={f} readOnly />
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Verbatim Evidence Panel */}
        <div className="lg:col-span-5 bg-document border border-document-rule rounded-lg p-6 font-mono text-document-ink sticky top-24 self-start max-h-[calc(100vh-140px)] overflow-y-auto">
          <div className="border-b border-document-rule pb-4 mb-6">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-document-soft" />
              <p className="font-mono text-xs text-document-soft uppercase tracking-wider font-semibold">
                Verbatim Evidence
              </p>
            </div>
            <h3 className="font-mono font-bold text-sm text-document-ink mt-2">
              CONTRACTUAL PROVENANCE REGISTER
            </h3>
            <div className="flex justify-between items-center mt-3 text-[10px] text-document-soft">
              <span>REF: {contract.id.toUpperCase()}</span>
              <span>CONFIDENCE: {activeFinding?.confidence?.toUpperCase() || "HIGH"}</span>
            </div>
          </div>

          {activeFinding ? (
            <div className="space-y-6">
              <div className="bg-document p-3 border border-document-rule rounded text-xs text-document-soft mb-4 leading-relaxed font-mono">
                📌 Showing verbatim clauses supporting the active finding above. Click other cards on the left to verify their source text.
              </div>
              
              {activeFinding.sources && activeFinding.sources.length > 0 ? (
                activeFinding.sources.map((s, i) => (
                  <div key={i} className="border-l-2 border-seal pl-4 py-1" data-testid={`demo-clause-${s.purpose}`}>
                    <div className="flex items-baseline justify-between gap-4 font-mono text-[10px] text-document-soft uppercase tracking-wider font-semibold">
                      <span>{PURPOSE_LABEL[s.purpose] || s.purpose}</span>
                      <span className="cc-section-ref !text-document-soft">{s.location}</span>
                    </div>
                    <p className="font-mono text-sm leading-relaxed text-document-ink mt-2 whitespace-pre-wrap">
                      &ldquo;{s.quote}&rdquo;
                    </p>
                  </div>
                ))
              ) : (
                <p className="font-mono text-xs text-document-soft">No verbatim quotes found for this finding.</p>
              )}
            </div>
          ) : (
            <p className="font-mono text-xs text-document-soft">Select a finding on the left to review its verbatim clause verification.</p>
          )}

          <div className="border-t border-document-rule pt-6 mt-8 flex justify-between items-center text-[10px] text-document-soft">
            <span className="font-mono uppercase tracking-wider">Provenance Engine</span>
            <span className="font-mono text-[9px] px-2 py-0.5 border border-document-soft rounded font-semibold uppercase">
              100% Verbatim Quote
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
