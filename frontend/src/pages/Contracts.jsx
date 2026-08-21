// Contracts — real list of the authenticated user's contracts (Stage 1).
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { Eyebrow } from "@/components/cc/Primitives";
import { CONTRACTS } from "@/constants/testIds";

const money = (v, cur) =>
  v == null ? null : new Intl.NumberFormat("en-US", {
    style: "currency", currency: cur || "USD", maximumFractionDigits: 0,
  }).format(v);

export default function Contracts() {
  const navigate = useNavigate();
  const [contracts, setContracts] = useState(null);

  useEffect(() => {
    api.get("/contracts").then((r) => setContracts(r.data.contracts)).catch(() => setContracts([]));
  }, []);

  return (
    <div data-testid={CONTRACTS.root}>
      <div className="flex items-end justify-between">
        <div>
          <Eyebrow>Contracts</Eyebrow>
          <div className="cc-seal-rule mt-4" />
        </div>
        <Button onClick={() => navigate("/app/upload")} data-testid="contracts-add"
          className="bg-ink text-paper hover:bg-ink/90 rounded-full h-10 px-5">
          Add a contract
        </Button>
      </div>

      <div className="mt-8">
        {contracts === null && <p className="cc-days-remaining">Loading…</p>}

        {contracts !== null && contracts.length === 0 && (
          <div className="rounded-lg border border-rule bg-card px-8 py-16 flex flex-col items-center text-center">
            <div className="h-12 w-12 rounded-full bg-card flex items-center justify-center">
              <FileText className="h-6 w-6 text-ink-soft" strokeWidth={1.75} />
            </div>
            <p className="cc-plain-english mt-5 max-w-sm">
              No contracts yet. Add one and ClauseClock reads the paper so you don&rsquo;t have to.
            </p>
            <Button onClick={() => navigate("/app/upload")} data-testid={CONTRACTS.emptyAddContract}
              className="mt-6 bg-ink text-paper hover:bg-ink/90 rounded-full h-11 px-6">
              Add a contract
            </Button>
          </div>
        )}

        {contracts && contracts.length > 0 && (
          <ul className="divide-y divide-rule rounded-lg border border-rule bg-card overflow-hidden">
            {contracts.map((c) => (
              <li key={c.id}>
                <button
                  data-testid={`contract-row-${c.id}`}
                  onClick={() => navigate(`/app/contracts/${c.id}`)}
                  className="w-full flex items-center justify-between px-6 py-5 text-left hover:bg-card/50 transition-colors duration-150"
                >
                  <div>
                    <p className="cc-finding-title">{c.name}</p>
                    <p className="cc-days-remaining mt-1">
                      {c.counterparty || "No counterparty"} · {c.document_count} document
                      {c.document_count === 1 ? "" : "s"}
                      {c.annual_value != null && <> · <span className="cc-money">{money(c.annual_value, c.currency)}</span></>}
                    </p>
                  </div>
                  <ChevronRight className="h-5 w-5 text-ink-soft" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
