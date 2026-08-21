import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Eyebrow } from "@/components/cc/Primitives";
import { buildDemoWorkspace } from "@/data/demoWorkspace";

const money = (v, cur) =>
  new Intl.NumberFormat("en-US", {
    style: "currency", currency: cur || "USD", maximumFractionDigits: 0,
  }).format(v);

export default function DemoContracts() {
  const navigate = useNavigate();
  const { contracts } = useMemo(() => buildDemoWorkspace(new Date()), []);

  return (
    <div data-testid="demo-contracts" className="max-w-4xl">
      <div className="flex items-center justify-between gap-4">
        <Eyebrow>Contracts</Eyebrow>
        <span className="cc-eyebrow px-3 py-1 rounded-full bg-card border border-rule text-ink-soft">
          Synthetic demo · read-only
        </span>
      </div>
      <div className="cc-seal-rule mt-4 mb-6" />
      <h1 className="font-archivo font-semibold text-ink text-2xl sm:text-3xl leading-tight">
        One portfolio. Different kinds of contract risk.
      </h1>
      <p className="cc-plain-english mt-3 text-ink-soft max-w-2xl">
        Open a contract to see the finding, its calculated timing, and the exact synthetic source language used to support it.
      </p>

      <ul className="mt-8 divide-y divide-rule rounded-lg border border-rule bg-card overflow-hidden">
        {contracts.map((c) => (
          <li key={c.id}>
            <button
              onClick={() => navigate(`/demo/contracts/${c.id}`)}
              className="w-full flex items-center justify-between px-6 py-5 text-left hover:bg-card/50 transition-colors"
            >
              <div>
                <p className="cc-finding-title">{c.name}</p>
                <p className="cc-days-remaining mt-1">
                  {c.counterparty} · <span className="cc-money">{money(c.annual_value, c.currency)}</span> · {c.findings.length} finding{c.findings.length === 1 ? "" : "s"}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-ink-soft" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
