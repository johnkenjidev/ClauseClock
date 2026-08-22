// /demo — public, read-only synthetic ClauseClock workspace (Stage 5).
// No auth, no backend. A mature portfolio opening on ranked What Matters,
// led by an urgent automatic-renewal finding 11 days out. Read-only: no
// Confirm/Correct/Dismiss, no Stage 6 actions/evidence/outcomes.
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Eyebrow } from "@/components/cc/Primitives";
import { FindingCard } from "@/components/cc/FindingCard";
import { buildDemoWorkspace } from "@/data/demoWorkspace";
import { DEMO } from "@/constants/testIds";

const money = (v, cur) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: cur || "USD", maximumFractionDigits: 0 }).format(v);

export default function Demo() {
  const navigate = useNavigate();
  const { contracts, whatMatters } = useMemo(() => buildDemoWorkspace(new Date()), []);

  return (
    <div data-testid={DEMO.root} className="max-w-6xl w-full mx-auto space-y-6">
      <div data-testid={DEMO.banner} className="bg-card border border-rule text-stamp font-mono text-xs uppercase tracking-widest py-3 px-4 text-center w-full block rounded border-l-4 border-l-stamp">
        ⚠️ Sandbox / Demo Environment — Synthetic Data Only (Read-Only)
      </div>

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <Eyebrow>Overview</Eyebrow>
          <h1 className="font-archivo font-black text-ink text-3xl sm:text-4xl tracking-tighter leading-tight mt-1">
            {contracts.length} contracts monitored. One needs attention.
          </h1>
          <p className="cc-plain-english mt-2 text-ink-soft max-w-2xl">
            This is a sample portfolio a few months into use — most contracts are calm,
            one automatic renewal is due soon. All data is synthetic and read-only.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
        <div className="bg-card border border-rule p-5 rounded">
          <span className="cc-eyebrow">Monitored Contracts</span>
          <p className="font-archivo font-bold text-ink text-3xl mt-2">5</p>
          <p className="cc-days-remaining mt-1 text-xs">All active agreements</p>
        </div>
        <div className="bg-card border border-rule p-5 rounded">
          <span className="cc-eyebrow">Value under tracking</span>
          <p className="font-archivo font-bold text-ink text-3xl mt-2">$242,400</p>
          <p className="cc-days-remaining mt-1 text-xs">Total tracked contract value</p>
        </div>
        <div className="bg-card border border-rule p-5 rounded">
          <span className="cc-eyebrow text-stamp">Actionable risks</span>
          <p className="font-archivo font-bold text-stamp text-3xl mt-2">1 Urgent</p>
          <p className="cc-days-remaining mt-1 text-xs text-stamp">Renewal is 11 days out</p>
        </div>
        <div className="bg-card border border-rule p-5 rounded">
          <span className="cc-eyebrow text-pending">Pending reviews</span>
          <p className="font-archivo font-bold text-pending text-3xl mt-2">1 Review</p>
          <p className="cc-days-remaining mt-1 text-xs text-pending">Missing effective date</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-10">
        {/* Left Area (What Matters) */}
        <div className="lg:col-span-8 space-y-6">
          <div>
            <div className="flex items-center justify-between">
              <Eyebrow>What matters</Eyebrow>
              <span className="cc-section-ref text-seal text-xs font-semibold uppercase tracking-wider">Ranked by Urgency</span>
            </div>
            <div className="cc-seal-rule mt-3 mb-2" />
            <p className="cc-days-remaining mb-5" data-testid="demo-clause-hint">
              Open any finding to reveal the exact contract language it came from.
            </p>
          </div>
          <div className="space-y-6" data-testid="demo-what-matters">
            {whatMatters.map(({ finding }) => (
              <FindingCard key={finding.id} finding={finding} readOnly />
            ))}
          </div>
        </div>

        {/* Right Area (All Contracts Sidebar) */}
        <div className="lg:col-span-4 space-y-6">
          <div>
            <Eyebrow>All contracts</Eyebrow>
            <div className="cc-seal-rule mt-3 mb-5" />
          </div>
          <ul className="divide-y divide-rule rounded border border-rule bg-card overflow-hidden">
            {contracts.map((c) => {
              const isUrgent = c.findings.some(f => f.id === "demo_f_urgent");
              const isReview = c.findings.some(f => f.validation_status === "needs_review");
              let badgeText = "";
              let badgeCls = "";
              if (isUrgent) {
                badgeText = "Urgent";
                badgeCls = "bg-stamp/10 text-stamp border-stamp/20";
              } else if (isReview) {
                badgeText = "Review";
                badgeCls = "bg-pending/10 text-pending border-pending/20";
              } else {
                badgeText = "Calm";
                badgeCls = "bg-seal/10 text-seal border-seal/20";
              }

              return (
                <li key={c.id}>
                  <button data-testid={`demo-contract-${c.id}`}
                    onClick={() => navigate(`/demo/contracts/${c.id}`)}
                    className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-paper transition-colors group">
                    <div className="pr-2">
                      <p className="cc-finding-title text-sm group-hover:text-seal transition-colors">{c.name}</p>
                      <p className="cc-days-remaining text-xs mt-1">
                        {c.counterparty} · <span className="cc-money text-xs">{money(c.annual_value, c.currency)}</span>
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${badgeCls}`}>
                        {badgeText}
                      </span>
                      <ChevronRight className="h-4 w-4 text-ink-soft group-hover:text-ink transition-colors" />
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>

          {/* Sandbox info panel */}
          <div className="p-5 border border-rule bg-card/40 rounded space-y-3">
            <span className="cc-eyebrow">Sandbox Environment</span>
            <p className="text-xs cc-days-remaining leading-relaxed">
              This read-only portal lets prospective users evaluate the ClauseClock extraction and provenance engine without uploading live contracts.
            </p>
            <div className="flex flex-col gap-2 pt-2 text-xs">
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-stamp shrink-0" />
                <span>Stamp: urgent action required (≤ 14 days)</span>
              </span>
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-pending shrink-0" />
                <span>Pending: approaching notice date / review needed</span>
              </span>
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-seal shrink-0" />
                <span>Seal: calm or confirmed status</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
