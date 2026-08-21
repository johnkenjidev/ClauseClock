// /demo — public, read-only synthetic ClauseClock workspace.
// No auth and no real customer data. It intentionally exercises the same
// FindingCard used by the authenticated product.
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
  const { contracts, whatMatters, actionItems } = useMemo(() => buildDemoWorkspace(new Date()), []);

  return (
    <div data-testid={DEMO.root} className="max-w-3xl">
      <div className="flex items-center justify-between gap-4">
        <Eyebrow>Overview</Eyebrow>
        <span data-testid={DEMO.banner}
          className="cc-eyebrow px-3 py-1 rounded-full bg-card border border-rule text-ink-soft">
          Synthetic demo workspace · read-only
        </span>
      </div>
      <div className="cc-seal-rule mt-4 mb-6" />

      <h1 className="font-archivo font-semibold text-ink text-2xl sm:text-3xl leading-tight">
        {contracts.length} contracts monitored. {actionItems.length} confirmed actions have a deadline.
      </h1>
      <p className="cc-plain-english mt-3 text-ink-soft">
        This sample portfolio shows automatic renewal, a price increase, an invoice-dispute window,
        an early-exit right, a service-credit opportunity, and one finding ClauseClock refuses to date
        until a missing fact is confirmed. All data is synthetic.
      </p>

      <div className="mt-10">
        <Eyebrow>What matters</Eyebrow>
        <div className="cc-seal-rule mt-3 mb-2" />
        <p className="cc-days-remaining mb-5 max-w-xl" data-testid="demo-clause-hint">
          Open any finding to reveal the exact synthetic contract language that supports it.
        </p>
        <div className="space-y-6" data-testid="demo-what-matters">
          {whatMatters.map(({ finding }) => (
            <FindingCard key={finding.id} finding={finding} readOnly />
          ))}
        </div>
      </div>

      <div className="mt-12">
        <div className="flex items-center justify-between gap-4">
          <Eyebrow>All contracts</Eyebrow>
          <button onClick={() => navigate("/demo/actions")}
            className="cc-section-ref text-seal hover:underline">
            Open Action Center →
          </button>
        </div>
        <div className="cc-seal-rule mt-3 mb-5" />
        <ul className="divide-y divide-rule rounded-lg border border-rule bg-card overflow-hidden">
          {contracts.map((c) => (
            <li key={c.id}>
              <button data-testid={`demo-contract-${c.id}`}
                onClick={() => navigate(`/demo/contracts/${c.id}`)}
                className="w-full flex items-center justify-between px-6 py-5 text-left hover:bg-card/50 transition-colors">
                <div>
                  <p className="cc-finding-title">{c.name}</p>
                  <p className="cc-days-remaining mt-1">
                    {c.counterparty} · <span className="cc-money">{money(c.annual_value, c.currency)}</span>
                  </p>
                </div>
                <ChevronRight className="h-5 w-5 text-ink-soft" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
