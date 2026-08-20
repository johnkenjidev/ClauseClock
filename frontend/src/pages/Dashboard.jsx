// Dashboard — Stage 6C2 value accounting. When the workspace has contracts we
// surface the headline figures (contracts monitored, value under tracking,
// confirmed value protected, pending value, windows missed). Confirmed value
// protected counts CONFIRMED outcomes only; the server owns all the math.
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Eyebrow } from "@/components/cc/Primitives";
import { LegalFooter } from "@/components/cc/Primitives";
import { api } from "@/lib/api";
import { DASHBOARD } from "@/constants/testIds";

function money(amount, currency) {
  const n = Number(amount || 0);
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: 0,
    }).format(n);
  } catch {
    return `${currency || "USD"} ${Math.round(n).toLocaleString()}`;
  }
}

const StatCard = ({ label, value, sub, testId, tone }) => (
  <div
    data-testid={testId}
    className="rounded-lg border border-rule bg-paper p-6"
  >
    <p className="cc-eyebrow">{label}</p>
    <p
      className={
        "mt-3 font-archivo font-semibold tabular-nums text-3xl leading-none " +
        (tone === "seal" ? "text-ink" : "text-ink")
      }
      style={{ fontVariantNumeric: "tabular-nums" }}
    >
      {value}
    </p>
    {sub ? <p className="cc-days-remaining mt-2">{sub}</p> : null}
  </div>
);

export default function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api
      .get("/dashboard/summary")
      .then((r) => setSummary(r.data))
      .catch(() => setSummary(null))
      .finally(() => setLoaded(true));
  }, []);

  const hasContracts = summary && summary.contracts_monitored > 0;

  if (!loaded) {
    return <div data-testid={DASHBOARD.root} className="max-w-2xl" />;
  }

  // Empty state (PART 5.5) — unchanged for a workspace with no contracts.
  if (!hasContracts) {
    return (
      <div data-testid={DASHBOARD.root} className="max-w-2xl">
        <Eyebrow>Your workspace</Eyebrow>
        <div className="cc-seal-rule mt-4 mb-6" />
        <h1 className="font-archivo font-semibold text-ink text-3xl sm:text-4xl leading-tight tracking-tight">
          Add a contract and ClauseClock finds the
          <br className="hidden sm:block" /> deadlines that cost money.
        </h1>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button
            data-testid={DASHBOARD.emptyAddContract}
            onClick={() => navigate("/app/upload")}
            className="bg-ink text-paper hover:bg-ink/90 rounded-full h-11 px-6"
          >
            Add a contract
          </Button>
          <Button
            variant="outline"
            data-testid={DASHBOARD.emptySample}
            onClick={() => navigate("/app/contracts")}
            className="rounded-full h-11 px-6 border-rule text-ink hover:bg-document"
          >
            View your contracts
          </Button>
        </div>
      </div>
    );
  }

  const cur = summary.currency || "USD";

  return (
    <div data-testid={DASHBOARD.root} className="max-w-5xl">
      <Eyebrow>Your workspace</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-6" />

      {/* Headline — confirmed value protected (confirmed outcomes only). */}
      <div
        data-testid={DASHBOARD.confirmedValueProtected}
        className="rounded-lg border border-rule bg-document p-8"
      >
        <p className="cc-eyebrow">Confirmed value protected &amp; recovered</p>
        <p className="cc-hero-date mt-4">
          {money(summary.confirmed_value_protected, cur)}
        </p>
        <p className="cc-days-remaining mt-3">
          From confirmed outcomes only.
          {summary.pending_value > 0
            ? ` ${money(summary.pending_value, cur)} pending confirmation.`
            : " No outcomes are awaiting confirmation."}
        </p>
      </div>

      <div
        data-testid={DASHBOARD.metrics}
        className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        <StatCard
          testId={DASHBOARD.contractsMonitored}
          label="Contracts monitored"
          value={summary.contracts_monitored}
        />
        <StatCard
          testId={DASHBOARD.valueUnderTracking}
          label="Value under tracking"
          value={money(summary.value_under_tracking, cur)}
          sub="Total annual contract value"
        />
        <StatCard
          testId={DASHBOARD.pendingValue}
          label="Pending value"
          value={money(summary.pending_value, cur)}
          sub="Recorded, awaiting confirmation"
        />
        <StatCard
          testId={DASHBOARD.windowsMissed}
          label="Windows missed"
          value={summary.windows_missed}
          sub="Deadlines recorded as missed"
        />
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <Button
          onClick={() => navigate("/app/upload")}
          className="bg-ink text-paper hover:bg-ink/90 rounded-full h-11 px-6"
        >
          Add a contract
        </Button>
        <Button
          variant="outline"
          onClick={() => navigate("/app/action-center")}
          className="rounded-full h-11 px-6 border-rule text-ink hover:bg-document"
        >
          Go to Action Center
        </Button>
      </div>

      <div className="mt-10">
        <LegalFooter />
      </div>
    </div>
  );
}
