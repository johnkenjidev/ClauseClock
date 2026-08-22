// /demo — public, read-only synthetic ClauseClock V2 workspace.
// Showcase of the three proof moments: sourced finding → safe refusal → evidence/outcome record.
import { useNavigate } from "react-router-dom";
import { Eyebrow } from "@/components/cc/Primitives";
import { FileText, Check, AlertTriangle, HelpCircle } from "lucide-react";
import { DEMO } from "@/constants/testIds";

export default function Demo() {
  const navigate = useNavigate();

  return (
    <div data-testid={DEMO.root} className="max-w-4xl w-full mx-auto space-y-12">
      {/* Pinned top sandbox banner */}
      <div 
        data-testid={DEMO.banner} 
        className="bg-card border border-rule text-ink font-mono text-[11px] uppercase tracking-widest py-3 px-5 text-center w-full block rounded-none sm:rounded border-l-4 border-l-seal"
      >
        Sandbox / Demo Workspace — Synthetic Data Only
      </div>

      {/* Header */}
      <div className="space-y-3">
        <Eyebrow>PROVENANCE WORKSPACE V2</Eyebrow>
        <h1 className="font-archivo font-black text-ink text-3xl sm:text-5xl tracking-tighter leading-tight">
          Proof of Grounded Math.
        </h1>
        <p className="font-archivo text-base text-ink-soft leading-relaxed max-w-2xl">
          Three visual moments demonstrating the ClauseClock engine: deterministic calculations, zero AI estimation fallbacks, and audited evidence.
        </p>
      </div>

      <div className="cc-seal-rule w-16" />

      {/* Moment 1: Sourced Finding */}
      <section className="space-y-6 pt-4">
        <div className="space-y-2">
          <span className="font-mono text-xs text-ink-soft tracking-wider font-semibold">MOMENT 01</span>
          <h2 className="font-archivo font-bold text-xl sm:text-2xl text-ink tracking-tight">Sourced Finding & Absolute Anchor</h2>
          <p className="font-archivo text-sm text-ink-soft max-w-2xl leading-relaxed">
            Deterministic calendar dates computed directly from classified contract anchors.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Summary */}
          <div className="lg:col-span-6 bg-card border border-rule p-5 sm:p-6 rounded-none sm:rounded space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <span className="font-mono text-[11px] text-ink-soft uppercase tracking-wider font-semibold">Contract Title</span>
                <h3 className="font-archivo font-semibold text-lg text-ink mt-0.5">Meridian Data Processing Agreement</h3>
              </div>
              <span className="font-mono text-[10px] text-seal uppercase font-bold tracking-wider px-2 py-0.5 rounded border border-rule bg-paper">
                Verified
              </span>
            </div>

            <div className="pt-2">
              <span className="font-mono text-[11px] text-ink-soft uppercase tracking-wider font-semibold">Calculated Deadline</span>
              <p className="font-archivo font-black text-ink text-3xl sm:text-4xl mt-1 tracking-tight">
                October 1, 2028
              </p>
              <p className="font-archivo text-xs text-ink-soft mt-1 leading-relaxed">
                Calculated strictly backwards by 30 days from the next renewal date (renewal_start anchor).
              </p>
            </div>

            <div className="pt-2 grid grid-cols-2 gap-4 border-t border-rule">
              <div>
                <span className="font-mono text-[10px] text-ink-soft uppercase tracking-wider">ANCHOR TYPE</span>
                <p className="font-archivo text-sm text-ink font-semibold mt-1">Renewal Start</p>
              </div>
              <div>
                <span className="font-mono text-[10px] text-ink-soft uppercase tracking-wider">NOTICE WINDOW</span>
                <p className="font-archivo text-sm text-ink font-semibold mt-1">30 Days</p>
              </div>
            </div>
          </div>

          {/* Evidence surface: full-bleed below 640px */}
          <div className="lg:col-span-6 bg-document border border-document-rule p-5 sm:p-6 rounded-none sm:rounded-lg font-mono text-document-ink space-y-4 w-full">
            <div className="flex items-center justify-between border-b border-document-rule pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-document-soft" />
                <span className="text-[11px] text-document-soft uppercase tracking-wider font-bold">Verbatim Contract Clause</span>
              </div>
              <span className="text-[10px] text-document-soft font-semibold">P.3</span>
            </div>

            <p className="font-mono text-sm leading-relaxed text-document-ink whitespace-pre-wrap">
              &ldquo;The subscription will renew automatically for successive annual terms unless notice is given at least thirty (30) days prior to renewal.&rdquo;
            </p>

            <div className="border-t border-document-rule pt-3 text-[10px] text-document-soft space-y-1">
              <p className="font-mono">source_hash: a8f7c9e13b8d4e92b3c7d6a5d4f1c3b4e9a8d7c6f5e4d3c2b1a0e9f8</p>
              <p className="font-mono">char_offset: [14,288 - 14,440]</p>
            </div>
          </div>
        </div>
      </section>

      <div className="border-t border-rule" />

      {/* Moment 2: Safe Refusal */}
      <section className="space-y-6 pt-4">
        <div className="space-y-2">
          <span className="font-mono text-xs text-ink-soft tracking-wider font-semibold">MOMENT 02</span>
          <h2 className="font-archivo font-bold text-xl sm:text-2xl text-ink tracking-tight">Safe Refusal (Non-Hallucination Invariant)</h2>
          <p className="font-archivo text-sm text-ink-soft max-w-2xl leading-relaxed">
            ClauseClock refuses to estimate missing terms. If a reference date cannot be proven, no date calculations are performed.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Summary */}
          <div className="lg:col-span-6 bg-card border border-rule p-5 sm:p-6 rounded-none sm:rounded space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <span className="font-mono text-[11px] text-ink-soft uppercase tracking-wider font-semibold">Contract Title</span>
                <h3 className="font-archivo font-semibold text-lg text-ink mt-0.5">Harbor Logistics Master Services Agreement</h3>
              </div>
              <span className="font-mono text-[10px] text-pending uppercase font-bold tracking-wider px-2 py-0.5 rounded border border-rule bg-paper flex items-center gap-1 shrink-0">
                <HelpCircle className="h-3 w-3" /> Needs Review
              </span>
            </div>

            <div className="pt-2 space-y-3">
              <span className="font-mono text-[11px] text-pending uppercase tracking-wider font-semibold">State Invariant</span>
              <div className="bg-paper border border-rule p-4 flex gap-3 rounded-none">
                <AlertTriangle className="h-5 w-5 text-pending shrink-0 mt-0.5" />
                <p className="font-archivo text-xs leading-relaxed text-ink">
                  <span className="font-semibold text-pending">Cannot compute from this document</span> — Missing agreement effective date. Absolute deadlines cannot be mathematically resolved without speculative inference.
                </p>
              </div>
            </div>

            <div className="pt-2 grid grid-cols-2 gap-4 border-t border-rule">
              <div>
                <span className="font-mono text-[10px] text-ink-soft uppercase tracking-wider">EXTRACTED TYPE</span>
                <p className="font-archivo text-sm text-ink font-semibold mt-1">Automatic Renewal</p>
              </div>
              <div>
                <span className="font-mono text-[10px] text-ink-soft uppercase tracking-wider">NOTICE REQUIRED</span>
                <p className="font-archivo text-sm text-ink font-semibold mt-1">60 Days</p>
              </div>
            </div>
          </div>

          {/* Evidence surface: full-bleed below 640px */}
          <div className="lg:col-span-6 bg-document border border-document-rule p-5 sm:p-6 rounded-none sm:rounded-lg font-mono text-document-ink space-y-4 w-full">
            <div className="flex items-center justify-between border-b border-document-rule pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-document-soft" />
                <span className="text-[11px] text-document-soft uppercase tracking-wider font-bold">Verbatim Contract Clause</span>
              </div>
              <span className="text-[10px] text-document-soft font-semibold">P.5</span>
            </div>

            <p className="font-mono text-sm leading-relaxed text-document-ink whitespace-pre-wrap">
              &ldquo;This MSA renews automatically for one-year terms unless terminated with sixty (60) days notice.&rdquo;
            </p>

            <div className="border-t border-document-rule pt-3 text-[10px] text-document-soft space-y-1">
              <p className="font-mono">source_hash: c9d8e7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2</p>
              <p className="font-mono">char_offset: [21,040 - 21,142]</p>
            </div>
          </div>
        </div>
      </section>

      <div className="border-t border-rule" />

      {/* Moment 3: Evidence/Outcome Record */}
      <section className="space-y-6 pt-4">
        <div className="space-y-2">
          <span className="font-mono text-xs text-ink-soft tracking-wider font-semibold">MOMENT 03</span>
          <h2 className="font-archivo font-bold text-xl sm:text-2xl text-ink tracking-tight">Evidence & Outcome Ledger</h2>
          <p className="font-archivo text-sm text-ink-soft max-w-2xl leading-relaxed">
            Locked action logs and outcome validation tracking. Standard ledger rows stack vertically below 480px.
          </p>
        </div>

        {/* Ledger Table */}
        <div className="border border-rule bg-card rounded-none sm:rounded overflow-hidden divide-y divide-rule">
          {/* Header row - hidden below 480px for stacking */}
          <div className="hidden xs:flex items-center justify-between px-5 py-3 bg-paper/50 font-mono text-[10px] text-ink-soft uppercase tracking-wider font-bold border-b border-rule">
            <span className="w-1/3">Timestamp & Reference</span>
            <span className="w-1/3">Event Action</span>
            <span className="w-1/3 text-right">Verification Token / Value</span>
          </div>

          {/* Row 1 */}
          <div className="p-5 flex flex-col xs:flex-row xs:items-center justify-between gap-4 text-sm">
            <div className="xs:w-1/3 flex flex-col gap-0.5">
              <span className="font-mono text-[11px] text-ink-soft">2028-09-01 10:14:00 UTC</span>
              <span className="font-mono text-[10px] text-ink-soft font-semibold">LOG-ID: CC-EV-9123</span>
            </div>
            
            <div className="xs:w-1/3 flex flex-col gap-0.5">
              <span className="font-archivo font-semibold text-ink text-xs uppercase tracking-wide">Non-Renewal Notice Logged</span>
              <span className="text-xs text-ink-soft leading-relaxed">Written notice delivered by certified mail to Meridian Systems General Counsel.</span>
            </div>

            <div className="xs:w-1/3 flex flex-col xs:items-end gap-1">
              <span className="font-mono text-xs text-ink border border-rule px-2 py-0.5 rounded bg-paper self-start xs:self-auto flex items-center gap-1 font-semibold">
                <Check className="h-3 w-3 text-seal" /> cert_9405500000
              </span>
              <span className="font-mono text-[9px] text-ink-soft">sha256: 8f2b3c...f231</span>
            </div>
          </div>

          {/* Row 2 */}
          <div className="p-5 flex flex-col xs:flex-row xs:items-center justify-between gap-4 text-sm">
            <div className="xs:w-1/3 flex flex-col gap-0.5">
              <span className="font-mono text-[11px] text-ink-soft">2028-09-15 14:22:10 UTC</span>
              <span className="font-mono text-[10px] text-ink-soft font-semibold">LOG-ID: CC-EV-9124</span>
            </div>
            
            <div className="xs:w-1/3 flex flex-col gap-0.5">
              <span className="font-archivo font-semibold text-ink text-xs uppercase tracking-wide">Outcome Confirmed</span>
              <span className="text-xs text-ink-soft leading-relaxed">Meridian Systems acknowledged termination. Contract status updated to Terminated.</span>
            </div>

            <div className="xs:w-1/3 flex flex-col xs:items-end gap-1">
              <span className="font-mono text-xs text-seal font-semibold uppercase tracking-wider">
                Value Avoided: $26,400
              </span>
              <span className="font-mono text-[9px] text-ink-soft">sha256: a1c9e8...c914</span>
            </div>
          </div>
        </div>
      </section>

      {/* End CTA */}
      <section className="pt-8 border-t border-rule text-center">
        <button 
          onClick={() => navigate("/signup")}
          className="px-8 py-4 bg-ink text-paper hover:bg-ink-soft transition-colors font-archivo font-bold text-xs tracking-widest uppercase border border-rule rounded-none shadow-none"
        >
          Start Monitored Tracking
        </button>
      </section>
    </div>
  );
}
