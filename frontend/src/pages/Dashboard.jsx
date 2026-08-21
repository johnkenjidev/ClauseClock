// Dashboard — Stage 6C2 value accounting. When the workspace has contracts we
// surface the headline figures (contracts monitored, value under tracking,
// confirmed value protected, pending value, windows missed). Confirmed value
// protected counts CONFIRMED outcomes only; the server owns all the math.
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Download } from "lucide-react";
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

const longDate = (iso) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
};

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
  const [reminders, setReminders] = useState({ reminders: [], due_count: 0 });
  const [byContract, setByContract] = useState([]);

  useEffect(() => {
    api
      .get("/dashboard/summary")
      .then((r) => setSummary(r.data))
      .catch(() => setSummary(null))
      .finally(() => setLoaded(true));
    api.get("/reminders").then((r) => setReminders(r.data)).catch(() => {});
    api.get("/dashboard/value-by-contract").then((r) => setByContract(r.data.contracts || [])).catch(() => {});
  }, []);

  const downloadReport = async () => {
    const { data } = await api.get("/reports/savings");
    const rows = [["Contract", "Outcome", "Value", "Currency", "Recorded", "Notes"]];
    (data.lines || []).forEach((l) =>
      rows.push([l.contract_name, l.result, l.value, l.currency, l.recorded_at, (l.notes || "").replace(/[\n,]/g, " ")]));
    const header =
      `ClauseClock Savings Report\nGenerated,${data.generated_at}\n` +
      `Confirmed value protected/recovered,${data.currency} ${data.confirmed_value_protected}\n` +
      `Pending (not in headline),${data.currency} ${data.pending_value}\n\n`;
    const csv = header + rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `clauseclock-savings-${data.generated_at.slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const hasContracts = summary && summary.contracts_monitored > 0;

  if (!loaded) {
    return <div data-testid={DASHBOARD.root} className="max-w-2xl" />;
  }

  // Empty state — first-use orientation. Disappears naturally once contracts
  // exist; no onboarding/dismissal state.
  if (!hasContracts) {
    const steps = [
      ["Add the complete contract",
       "Upload the main agreement plus any amendments, order forms, exhibits, or SLAs that may change its terms."],
      ["Review what matters",
       "ClauseClock shows the deadline or financial term beside the exact source language it came from."],
      ["Act and keep the record",
       "Confirm or correct the finding, prepare a notice, log what you sent, attach evidence, and record the outcome."],
    ];
    return (
      <div data-testid={DASHBOARD.root} className="max-w-2xl">
        <Eyebrow>Your workspace</Eyebrow>
        <div className="cc-seal-rule mt-4 mb-6" />
        <h1 className="font-archivo font-semibold text-ink text-3xl sm:text-4xl leading-tight tracking-tight">
          Know what matters before the deadline does.
        </h1>
        <p className="cc-plain-english text-ink-soft mt-4 max-w-xl">
          ClauseClock finds renewal and pricing terms, verifies them against the original
          contract language, and helps you act on them.
        </p>

        <div className="mt-8 space-y-5">
          {steps.map(([title, body]) => (
            <div key={title} className="rounded-lg border border-rule bg-card p-5">
              <p className="cc-finding-title text-ink text-[16px]">{title}</p>
              <p className="cc-days-remaining mt-1.5 max-w-xl">{body}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Button
            data-testid={DASHBOARD.emptyAddContract}
            onClick={() => navigate("/app/upload")}
            className="bg-ink text-paper hover:bg-ink/90 rounded-full h-11 px-6"
          >
            Add a contract
          </Button>
          <Button
            variant="ghost"
            data-testid={DASHBOARD.emptySample}
            onClick={() => navigate("/demo")}
            className="rounded-full h-11 px-4 text-ink-soft hover:text-ink hover:bg-card"
          >
            See a sample workspace →
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
        className="rounded-lg border border-rule bg-card p-8"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
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
          <Button
            variant="outline"
            data-testid={DASHBOARD.savingsReportBtn}
            onClick={downloadReport}
            className="rounded-full h-10 px-4 gap-1.5 border-rule text-ink hover:bg-paper shrink-0"
          >
            <Download className="h-4 w-4" /> Savings report
          </Button>
        </div>
      </div>

      {/* Reminders due (in-app, no scheduler) */}
      {reminders.due_count > 0 && (
        <div data-testid={DASHBOARD.remindersDue} className="mt-6 rounded-lg border border-pending/40 bg-paper p-6">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-pending" strokeWidth={2} />
            <p className="cc-eyebrow">Reminders due ({reminders.due_count})</p>
          </div>
          <ul className="mt-4 space-y-2">
            {reminders.reminders.filter((r) => r.due).map((r) => (
              <li key={r.id}
                className="flex items-center justify-between rounded-md border border-rule bg-card px-4 py-2 cursor-pointer hover:bg-card/70"
                onClick={() => navigate(`/app/contracts/${r.contract_id}`)}>
                <span className="cc-plain-english text-ink">{r.contract_name || "Contract"}</span>
                <span className="cc-days-remaining">deadline {longDate(r.deadline)} · reminder set {r.days_before}d before</span>
              </li>
            ))}
          </ul>
        </div>
      )}

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

      {byContract.length > 0 && (
        <div data-testid={DASHBOARD.valueByContract} className="mt-8">
          <Eyebrow>Value by contract</Eyebrow>
          <div className="cc-seal-rule mt-4 mb-5" />
          <div className="rounded-lg border border-rule bg-paper overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-rule">
                  <th className="cc-eyebrow px-5 py-3">Contract</th>
                  <th className="cc-eyebrow px-5 py-3 text-right">Confirmed</th>
                  <th className="cc-eyebrow px-5 py-3 text-right">Pending</th>
                  <th className="cc-eyebrow px-5 py-3 text-right">Outcomes</th>
                </tr>
              </thead>
              <tbody>
                {byContract.map((c) => (
                  <tr key={c.contract_id}
                    className="border-b border-rule/60 last:border-0 cursor-pointer hover:bg-card/50"
                    data-testid={`value-row-${c.contract_id}`}
                    onClick={() => navigate(`/app/contracts/${c.contract_id}`)}>
                    <td className="cc-plain-english px-5 py-3 text-ink">{c.name}</td>
                    <td className="cc-money px-5 py-3 text-right">{money(c.confirmed_value, c.currency)}</td>
                    <td className="cc-days-remaining px-5 py-3 text-right">{money(c.pending_value, c.currency)}</td>
                    <td className="cc-days-remaining px-5 py-3 text-right">{c.outcome_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

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
          className="rounded-full h-11 px-6 border-rule text-ink hover:bg-card"
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
