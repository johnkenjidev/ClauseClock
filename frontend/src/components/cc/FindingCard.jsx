// FindingCard — Stage 2 renewal_notice display + the signature clause drawer.
// Summary register (calm, white) with the hero deadline; evidence register
// (verbatim, --document ground) grouped by purpose with server-resolved
// source locations. No plain-English explanations (that is Stage 4).
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Check, Pencil, X, Bell, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { LegalFooter } from "@/components/cc/Primitives";
import { CorrectFindingDialog } from "@/components/cc/CorrectFindingDialog";

const STATE_BADGE = {
  confirmed: { label: "Confirmed", cls: "bg-seal text-paper" },
  corrected: { label: "Corrected", cls: "bg-seal text-paper" },
  dismissed: { label: "Dismissed", cls: "bg-document text-ink-soft border border-rule" },
};

const PURPOSE_LABEL = {
  effective_date: "Effective date",
  renewal_term: "Renewal term",
  notice_period: "Notice period",
  notice_method: "Notice method",
  notice_recipient: "Notice recipient",
  business_day_definition: "Business day definition",
  deemed_receipt: "Deemed receipt",
  value: "Contract value",
  increase: "Price increase",
  objection: "Objection window",
  increase_basis: "What it applies to",
};

const INCREASE_TYPE_LABEL = {
  fixed_automatic: "Fixed automatic",
  capped: "Capped (maximum)",
  formula: "Formula / index-linked",
  unspecified: "Unspecified",
};

const MONTHS = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];

function heroDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}`;
}
function longDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US",
    { year: "numeric", month: "long", day: "numeric" });
}
const money = (v, cur) =>
  v == null ? null : new Intl.NumberFormat("en-US",
    { style: "currency", currency: cur || "USD", maximumFractionDigits: 0 }).format(v);

// price_increase presentation helpers
function rateText(e) {
  if (e.increase_type === "formula") return e.increase_formula || "Formula (not stated)";
  if (e.increase_percent != null)
    return `${e.increase_percent}%${e.increase_type === "capped" ? " (max)" : ""}`;
  if (e.increase_amount != null) return money(e.increase_amount) || "Not stated";
  return "Not stated";
}
function objectionWindowText(e) {
  if (e.objection_window_value == null) return null;
  const unit = e.objection_window_unit || "days";
  const b = e.objection_basis === "business" ? " business" : "";
  return `${e.objection_window_value}${b} ${unit}`;
}
function priceHeadline(e) {
  if (e.increase_type === "formula") return (e.increase_formula || "FORMULA").toUpperCase();
  if (e.increase_type === "capped") return e.increase_percent != null ? `UP TO ${e.increase_percent}%` : "CAPPED";
  if (e.increase_percent != null) return `+${e.increase_percent}%`;
  if (e.increase_amount != null) return `+${money(e.increase_amount)}`;
  return "INCREASE";
}
function priceSubhead(e) {
  if (e.increase_type === "capped") return "Maximum permitted increase — not guaranteed.";
  if (e.increase_type === "formula") return "Amount depends on the external index at the time.";
  if (e.next_term_amount != null) return "Applies automatically at the next term.";
  return "Stated price increase.";
}

// Palette selection per PART 5: stamp only ≤14d AND action required; pending
// for 15–60d / review; neutral otherwise.
function tone(f) {
  if (f.validation_status === "needs_review") return "pending";
  const dr = f.extracted?.days_remaining;
  if (dr == null) return "neutral";
  if (dr <= 14 && f.action_required) return "stamp";
  if (dr <= 60) return "pending";
  return "neutral";
}
const TONE_TEXT = { stamp: "text-stamp", pending: "text-pending", neutral: "text-ink" };
const TONE_RULE = { stamp: "bg-stamp", pending: "bg-pending", neutral: "bg-seal" };
const RANK_LABEL = {
  urgent: "Urgent", money: "Money", risk: "Risk",
  opportunity: "Opportunity", informational: "Informational",
};

export function FindingCard({ finding, onChanged, readOnly = false }) {
  const [open, setOpen] = useState(false);
  const [correctOpen, setCorrectOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const e = finding.extracted || {};
  const isPrice = finding.type === "price_increase";
  const t = tone(finding);
  const needsReview = finding.validation_status === "needs_review";
  const badge = STATE_BADGE[finding.state];

  const act = async (verb) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/findings/${finding.id}/${verb}`);
      onChanged?.(data.finding);
    } finally { setBusy(false); }
  };

  const grouped = {};
  for (const s of finding.sources || []) {
    (grouped[s.purpose] = grouped[s.purpose] || []).push(s);
  }
  const orderedPurposes = Object.keys(PURPOSE_LABEL).filter((p) => grouped[p]);

  const noticeText = () => {
    if (e.notice_days_min == null) return "Not stated";
    const basis = e.notice_basis === "business" ? "business days" : "days";
    if (e.notice_days_max != null)
      return `${e.notice_days_min}–${e.notice_days_max} ${basis}`;
    return `${e.notice_days_min} ${basis}`;
  };

  const heroIso = e.effective_action_deadline;

  return (
    <div data-testid={`finding-${finding.id}`}
      className="rounded-lg border border-rule bg-card overflow-hidden">
      <div className="p-6">
        <div className="flex items-start justify-between gap-6">
          <div>
            <p className="cc-eyebrow">{isPrice ? "Price increase" : "Automatic renewal"}</p>
            {finding.rank_category && (
              <span data-testid="finding-rank-category"
                className="inline-block cc-eyebrow mt-1 text-ink-soft">
                {RANK_LABEL[finding.rank_category]}
              </span>
            )}
            {needsReview ? (
              <>
                <p className={`cc-hero-date mt-3 ${TONE_TEXT[t]}`} data-testid="finding-needs-review">
                  NEEDS REVIEW
                </p>
                <p className="cc-days-remaining mt-2 max-w-md">
                  {finding.validation_notes?.[0] ||
                    "This finding needs review before a deadline can be shown."}
                </p>
              </>
            ) : isPrice && !heroIso ? (
              <>
                <p className={`cc-hero-date mt-3 ${TONE_TEXT[t]}`} data-testid="finding-price-headline">
                  {priceHeadline(e)}
                </p>
                <p className="cc-days-remaining mt-2 max-w-md" data-testid="finding-price-subhead">
                  {priceSubhead(e)}
                </p>
              </>
            ) : (
              <>
                <p className={`cc-hero-date mt-3 ${TONE_TEXT[t]}`} data-testid="finding-hero-date">
                  {heroDate(heroIso) || "—"}
                </p>
                <p className="cc-days-remaining mt-2" data-testid="finding-days-remaining">
                  {e.days_remaining != null
                    ? `${e.days_remaining} day${e.days_remaining === 1 ? "" : "s"} remaining`
                    : "Deadline not calculated"}
                </p>
              </>
            )}
          </div>
          <div className="text-right">
            {badge && (
              <span data-testid="finding-state-badge"
                className={`inline-block cc-eyebrow px-2.5 py-1 rounded-full mb-2 ${badge.cls}`}>
                {badge.label}
              </span>
            )}
            <p className="cc-eyebrow">Confidence</p>
            <p className={`cc-finding-title text-[16px] mt-1 capitalize ${TONE_TEXT[t]}`}
              data-testid="finding-confidence">{finding.confidence}</p>
          </div>
        </div>

        <div className={`mt-5 h-[3px] w-11 rounded ${TONE_RULE[t]}`} />

        {/* Key facts */}
        {isPrice ? (
          <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            <Fact label="Increase type"
              value={INCREASE_TYPE_LABEL[e.increase_type] || "Not stated"} testid="finding-increase-type" />
            <Fact label="Rate" value={rateText(e)} testid="finding-increase-rate" />
            {e.price_change_date && (
              <Fact label="Effective from" value={longDate(e.price_change_date)} testid="finding-price-change-date" />
            )}
            {e.next_term_amount != null && (
              <Fact label="Next-term value"
                value={<span className="cc-money">{money(e.next_term_amount, finding.money_currency)}</span>}
                testid="finding-next-term-amount" />
            )}
            {e.max_permitted_amount != null && (
              <Fact label="Maximum permitted"
                value={<span className="cc-money">{money(e.max_permitted_amount, finding.money_currency)}</span>}
                testid="finding-max-permitted" />
            )}
            {objectionWindowText(e) && (
              <Fact label="Objection window" value={objectionWindowText(e)} testid="finding-objection-window" />
            )}
            {!needsReview && e.objection_deadline && (
              <Fact label="Objection deadline" value={longDate(e.objection_deadline)} testid="finding-objection-deadline" />
            )}
            {e.increase_basis && (
              <Fact label="Applies to" value={e.increase_basis} testid="finding-increase-basis" />
            )}
            {finding.money_amount != null && (
              <Fact label={e.increase_type === "capped" ? "Maximum annual increase" : "Estimated annual increase"}
                value={<span className="cc-money">{money(finding.money_amount, finding.money_currency)}</span>}
                testid="finding-money" />
            )}
          </dl>
        ) : (
          <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            <Fact label="Next renewal"
              value={longDate(e.next_renewal_date) || "Not calculated"} testid="finding-next-renewal" />
            <Fact label="Notice period" value={noticeText()} testid="finding-notice-period" />
            {!needsReview && e.earliest_action_date && (
              <Fact label="Notice window"
                value={`${longDate(e.earliest_action_date)} – ${longDate(e.effective_action_deadline)}`}
                testid="finding-notice-window" />
            )}
            <Fact label="Notice method" value={e.notice_method || "Not stated"} testid="finding-notice-method" />
            <Fact label="Notice recipient" value={e.notice_recipient || "Not stated"} testid="finding-notice-recipient" />
            {finding.money_amount != null && (
              <Fact label="Contract value"
                value={<span className="cc-money">{money(finding.money_amount, finding.money_currency)}</span>}
                testid="finding-money" />
            )}
          </dl>
        )}

        {finding.validation_notes?.length > 0 && (
          <ul className="mt-5 space-y-1">
            {finding.validation_notes.map((n, i) => (
              <li key={i} className="cc-days-remaining text-pending" data-testid="finding-note">• {n}</li>
            ))}
          </ul>
        )}

        {/* Stage 4 explanation — derived ONLY from the validated clauses below.
            Never shown for needs_review; the clause drawer remains the evidence. */}
        {!needsReview && finding.plain_english && (
          <div className="mt-6 rounded-md border border-rule bg-card p-5" data-testid="finding-explanation">
            <p className="cc-eyebrow">In plain English</p>
            <p className="cc-plain-english mt-2" data-testid="finding-plain-english">{finding.plain_english}</p>
            {finding.why_it_matters && (
              <>
                <p className="cc-eyebrow mt-4">Why it matters</p>
                <p className="cc-plain-english mt-2" data-testid="finding-why">{finding.why_it_matters}</p>
              </>
            )}
            {finding.suggested_action && (
              <>
                <p className="cc-eyebrow mt-4">Suggested action</p>
                <p className="cc-plain-english mt-2" data-testid="finding-suggested-action">{finding.suggested_action}</p>
              </>
            )}
            <p className="cc-section-ref mt-4 text-ink-soft">
              Summarised from the cited clauses below — verify against the original contract.
            </p>
          </div>
        )}

        {/* Stage 3 actions: Confirm / Correct / Dismiss */}
        {!readOnly && (
        <div className="mt-6 flex flex-wrap items-center gap-2">
          <Button size="sm" disabled={busy} data-testid="finding-confirm-btn"
            onClick={() => act("confirm")}
            className="bg-seal text-paper hover:bg-seal/90 rounded-full h-9 px-4 gap-1.5">
            <Check className="h-4 w-4" strokeWidth={2.5} /> Confirm
          </Button>
          <Button size="sm" variant="outline" disabled={busy} data-testid="finding-correct-btn"
            onClick={() => setCorrectOpen(true)}
            className="rounded-full h-9 px-4 gap-1.5 border-rule text-ink hover:bg-document">
            <Pencil className="h-4 w-4" strokeWidth={2} /> Correct
          </Button>
          <Button size="sm" variant="ghost" disabled={busy} data-testid="finding-dismiss-btn"
            onClick={() => act("dismiss")}
            className="rounded-full h-9 px-4 gap-1.5 text-ink-soft hover:text-stamp hover:bg-document">
            <X className="h-4 w-4" strokeWidth={2} /> Dismiss
          </Button>
        </div>
        )}

        {!readOnly && !needsReview && heroIso && (
          <RemindersBlock findingId={finding.id} deadline={heroIso} />
        )}

        {/* Clause drawer toggle */}
        <button
          data-testid="clause-drawer-toggle"
          onClick={() => setOpen((o) => !o)}
          className="mt-6 cc-section-ref flex items-center gap-1.5 text-ink hover:text-seal transition-colors">
          Show the contract language
          <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
        </button>
      </div>

      {/* The signature clause drawer — evidence register on --document ground */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            data-testid="clause-drawer"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: "easeOut" }}
            className="bg-document border-t border-rule overflow-hidden">
            <div className="px-6 py-6 space-y-6">
              {orderedPurposes.map((purpose) =>
                grouped[purpose].map((s, i) => (
                  <div key={`${purpose}-${i}`} data-testid={`clause-${purpose}`}>
                    <div className="flex items-baseline justify-between gap-4">
                      <span className="cc-eyebrow">{PURPOSE_LABEL[purpose]}</span>
                      <span className="cc-section-ref">{s.location}</span>
                    </div>
                    <p className="cc-clause mt-2 text-ink">&ldquo;{s.quote}&rdquo;</p>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="px-6 py-5 border-t border-rule">
        <LegalFooter />
      </div>

      <CorrectFindingDialog finding={finding} open={correctOpen}
        onOpenChange={setCorrectOpen} onSaved={(f) => onChanged?.(f)} />
    </div>
  );
}

const Fact = ({ label, value, testid }) => (
  <div>
    <dt className="cc-eyebrow">{label}</dt>
    <dd className="cc-plain-english mt-1 text-ink" data-testid={testid}>{value}</dd>
  </div>
);

function RemindersBlock({ findingId, deadline }) {
  const [reminders, setReminders] = useState([]);
  const [days, setDays] = useState(30);
  const [busy, setBusy] = useState(false);
  const load = () =>
    api.get(`/findings/${findingId}/reminders`).then((r) => setReminders(r.data.reminders)).catch(() => {});
  useEffect(() => { load(); }, [findingId]);

  const add = async () => {
    setBusy(true);
    try { await api.post(`/findings/${findingId}/reminders`, { days_before: Number(days) }); load(); }
    finally { setBusy(false); }
  };
  const remove = async (id) => { await api.delete(`/reminders/${id}`); load(); };

  return (
    <div className="mt-6 pt-5 border-t border-rule" data-testid="reminders-block">
      <div className="flex items-center gap-2">
        <Bell className="h-4 w-4 text-ink-soft" strokeWidth={2} />
        <span className="cc-eyebrow">Deadline reminders</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="cc-days-remaining">Remind me</span>
        <input type="number" min="0" value={days} data-testid="reminder-days-input"
          onChange={(e) => setDays(e.target.value)}
          className="bg-card border border-rule rounded-md h-9 w-20 px-2 cc-days-remaining" />
        <span className="cc-days-remaining">days before the deadline</span>
        <Button size="sm" disabled={busy || days === "" } data-testid="reminder-add-btn" onClick={add}
          className="bg-ink text-paper hover:bg-ink/90 rounded-full h-9 px-4">
          {busy ? "Saving…" : "Set reminder"}
        </Button>
      </div>
      {reminders.length > 0 && (
        <ul className="mt-3 space-y-2" data-testid="reminders-list">
          {reminders.map((r) => (
            <li key={r.id} className="flex items-center justify-between rounded-md border border-rule bg-document px-4 py-2">
              <span className="cc-days-remaining text-ink" data-testid={`reminder-${r.id}`}>
                {r.days_before} days before · fires {longDate(r.fire_date)}
              </span>
              <button data-testid={`reminder-delete-${r.id}`} onClick={() => remove(r.id)}
                className="text-ink-soft hover:text-stamp"><Trash2 className="h-4 w-4" /></button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
