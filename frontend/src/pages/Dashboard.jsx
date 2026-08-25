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
import { localDaysRemaining } from "@/lib/dates";
import { DASHBOARD } from "@/constants/testIds";

const TYPE_LABEL = {
  renewal_notice: "Automatic renewal · notice required",
  termination_right: "Termination right · notice",
  price_increase: "Price increase · objection",
  service_credit: "Service credit · claim",
  invoice_dispute: "Invoice dispute · deadline",
  warranty_claim: "Warranty claim · deadline",
  rebate_or_refund: "Rebate / refund · claim",
  fee_or_penalty: "Fee / penalty · deadline",
  notice_requirement: "Notice requirement · deadline",
};

// Factual, neutral consequence line for a lapsed (already-past-deadline)
// current confirmed finding. No negative countdown, no urgency tone.
function lapsedConsequence(it) {
  const e = it.extracted || {};
  const deadlineTxt = longDate(e.effective_action_deadline);
  if (it.type === "renewal_notice") {
    return e.next_renewal_date
      ? `Non-renewal window closed ${deadlineTxt} \u00b7 Contract renews ${longDate(e.next_renewal_date)}`
      : `Non-renewal window closed ${deadlineTxt}`;
  }
  return `Action window closed ${deadlineTxt}`;
}

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
  const [actionCenter, setActionCenter] = useState(null);

  useEffect(() => {
    api
      .get("/dashboard/summary")
      .then((r) => setSummary(r.data))
      .catch(() => setSummary(null))
      .finally(() => setLoaded(true));
    api.get("/reminders").then((r) => setReminders(r.data)).catch(() => {});
    api.get("/dashboard/value-by-contract").then((r) => setByContract(r.data.contracts || [])).catch(() => {});
    api.get("/action-center").then((r) => setActionCenter(r.data)).catch(() => setActionCenter({ buckets: {}, count: 0 }));
  }, []);

  // Mobile hierarchy (Stage 30): built from the SAME current-finding /
  // supersession relationship Action Center already exposes — never
  // inferred from dates or deadline matching.
  const acItems = actionCenter
    ? [...(actionCenter.buckets?.urgent || []),
       ...(actionCenter.buckets?.next_30_days || []),
       ...(actionCenter.buckets?.later || [])]
    : [];
  const needsReviewItems = acItems.filter((it) => it.review_required);
  const lapsedItems = acItems.filter((it) => {
    if (it.review_required) return false;
    const dr = localDaysRemaining(it.extracted?.effective_action_deadline);
    if (dr == null || dr >= 0) return false;
    const nextRenewal = it.extracted?.next_renewal_date;
    if (nextRenewal) {
      const rdr = localDaysRemaining(nextRenewal);
      if (rdr != null && rdr < 0) return false; // consequence itself is past too — fully historical
    }
    return true;
  });
  const attentionItems = acItems.filter((it) => {
    if (it.review_required) return false;
    const dr = localDaysRemaining(it.extracted?.effective_action_deadline);
    return dr != null && dr >= 0;
  });
  const meaningfulByContract = byContract.filter(
    (c) => c.confirmed_value > 0 || c.pending_value > 0
  );

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
            className="bg-seal text-paper hover:bg-seal/90 rounded-full h-11 px-6"
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
    <div data-testid={DASHBOARD.root}>
      {/* Desktop-only layout */}
      <div className="hidden md:block max-w-5xl">
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
              className="rounded-full h-10 px-4 gap-1.5 border-rule text-ink hover:text-ink hover:bg-paper shrink-0"
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
            className="bg-seal text-paper hover:bg-seal/90 rounded-full h-11 px-6"
          >
            Add a contract
          </Button>
          <Button
            variant="outline"
            onClick={() => navigate("/app/action-center")}
            className="rounded-full h-11 px-6 border-rule text-ink hover:text-ink hover:bg-card"
          >
            Go to Action Center
          </Button>
        </div>
      </div>

      {/* Mobile-only layout (visible only below md breakpoint) */}
      <div className="md:hidden space-y-8 animate-cc-settle">

        {/* 1. Needs your review — only a current UNCONFIRMED superseding replacement */}
        {needsReviewItems.length > 0 && (
          <div data-testid={DASHBOARD.needsReview} className="space-y-3">
            <span className="cc-eyebrow">Needs your review</span>
            <ul className="space-y-2">
              {needsReviewItems.map((it) => (
                <li key={it.id} data-testid={`needs-review-item-${it.id}`}
                  className="flex flex-col gap-1.5 p-4 rounded bg-card border border-rule w-full min-w-0">
                  <span className="font-archivo font-semibold text-ink text-sm break-words min-w-0">{it.contract_name}</span>
                  <span className="cc-days-remaining text-xs leading-relaxed break-words text-ink-soft">
                    Contract terms changed — review before acting.
                  </span>
                  <button
                    onClick={() => navigate(`/app/contracts/${it.contract_id}`)}
                    data-testid={`needs-review-link-${it.id}`}
                    className="cc-eyebrow text-seal hover:text-seal/85 mt-1 font-semibold self-start"
                  >
                    Review changes →
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 2. Lapsed — current confirmed deadlines already passed, factual/neutral */}
        {lapsedItems.length > 0 && (
          <div data-testid={DASHBOARD.lapsed} className="space-y-3">
            <span className="cc-eyebrow">Lapsed</span>
            <ul className="space-y-2">
              {lapsedItems.map((it) => (
                <li key={it.id} data-testid={`lapsed-item-${it.id}`}
                  className="flex flex-col gap-1.5 p-4 rounded bg-card border border-rule w-full min-w-0">
                  <span className="font-archivo font-semibold text-ink text-sm break-words min-w-0">{it.contract_name}</span>
                  <span className="cc-days-remaining text-xs leading-relaxed break-words text-ink-soft">
                    {lapsedConsequence(it)}
                  </span>
                  <button
                    onClick={() => navigate(`/app/contracts/${it.contract_id}`)}
                    data-testid={`lapsed-view-contract-${it.id}`}
                    className="cc-eyebrow text-ink-soft hover:text-ink mt-1 font-semibold self-start"
                  >
                    View contract →
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 3. Attention — current live actionable deadlines only */}
        {attentionItems.length > 0 && (
          <div data-testid={DASHBOARD.attention} className="space-y-3">
            <span className="cc-eyebrow">Attention</span>
            <ul className="space-y-2">
              {attentionItems.map((it) => {
                const dr = localDaysRemaining(it.extracted?.effective_action_deadline);
                const urgent = dr != null && dr < 14;
                return (
                  <li key={it.id}
                    onClick={() => navigate("/app/action-center")}
                    data-testid={`attention-item-${it.id}`}
                    className="flex flex-col gap-1.5 p-4 rounded bg-card border border-rule cursor-pointer hover:bg-card/70 w-full min-w-0"
                  >
                    <span className="font-archivo font-semibold text-ink text-sm break-words min-w-0">{it.contract_name}</span>
                    <span className={"cc-days-remaining text-xs leading-relaxed break-words " + (urgent ? "text-stamp font-medium" : "text-ink-soft")}>
                      {TYPE_LABEL[it.type] || "Action required"} · deadline {longDate(it.extracted?.effective_action_deadline)} · {dr} days
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* 4. Portfolio — one compact line on the ground */}
        <div data-testid={DASHBOARD.portfolio} className="py-3 border-t border-b border-rule space-y-1">
          <p className="cc-days-remaining text-ink text-sm" data-testid={DASHBOARD.contractsMonitored}>
            {summary.contracts_monitored} {summary.contracts_monitored === 1 ? "contract" : "contracts"} · {money(summary.value_under_tracking, cur)} tracked
          </p>
          {summary.pending_value > 0 && (
            <p className="cc-days-remaining text-xs text-ink-soft" data-testid={DASHBOARD.pendingValue}>
              {money(summary.pending_value, cur)} pending confirmation
            </p>
          )}
          {summary.windows_missed > 0 && (
            <p className="cc-days-remaining text-xs text-ink-soft" data-testid={DASHBOARD.windowsMissed}>
              {summary.windows_missed} window{summary.windows_missed === 1 ? "" : "s"} missed
            </p>
          )}
        </div>

        {/* 5. Outcomes & protections */}
        <div data-testid={DASHBOARD.confirmedValueProtected} className="space-y-3">
          <span className="cc-eyebrow">Outcomes &amp; protections</span>
          {summary.confirmed_value_protected === 0 ? (
            <p className="cc-days-remaining text-ink-soft text-sm italic">No confirmed outcomes yet.</p>
          ) : (
            <div className="flex flex-col gap-1 bg-card/40 p-4 border border-rule rounded-sm">
              <span className="text-[10px] text-ink-soft font-bold uppercase tracking-wider">Confirmed value protected &amp; recovered</span>
              <p className="font-archivo font-black text-ink text-2xl mt-1">
                {money(summary.confirmed_value_protected, cur)}
              </p>
            </div>
          )}
          {(summary.confirmed_value_protected > 0 || summary.pending_value > 0) && (
            <div className="pt-1">
              <button
                data-testid={DASHBOARD.savingsReportBtn}
                onClick={downloadReport}
                className="border border-rule text-ink-soft hover:text-ink hover:border-ink-soft hover:bg-card rounded-full h-9 px-4 inline-flex items-center gap-1.5 bg-transparent cursor-pointer text-xs font-sans font-semibold transition-colors"
              >
                <Download className="h-3.5 w-3.5" /> Savings report
              </button>
            </div>
          )}
        </div>

        {/* 6. Value by contract — compact rows, meaningful/non-zero only */}
        {meaningfulByContract.length > 0 && (
          <div data-testid={DASHBOARD.valueByContract} className="space-y-3">
            <span className="cc-eyebrow">Value by contract</span>
            <div className="cc-seal-rule mt-2 mb-3" />
            <div className="border border-rule divide-y divide-rule bg-card rounded overflow-hidden">
              {meaningfulByContract.map((c) => (
                <div
                  key={c.contract_id}
                  onClick={() => navigate(`/app/contracts/${c.contract_id}`)}
                  className="p-4 flex flex-col gap-2 cursor-pointer hover:bg-card/70"
                  data-testid={`value-row-${c.contract_id}`}
                >
                  <div className="flex justify-between items-start gap-4">
                    <span className="font-archivo font-semibold text-ink text-sm break-words min-w-0 flex-1">{c.name}</span>
                    <span className="font-mono text-xs text-seal shrink-0">{money(c.confirmed_value, c.currency)}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs text-ink-soft">
                    <span>{c.outcome_count} {c.outcome_count === 1 ? "outcome" : "outcomes"}</span>
                    <span>Pending: {money(c.pending_value, c.currency)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
