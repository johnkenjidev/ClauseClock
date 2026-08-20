// FindingCard — Stage 2 renewal_notice display + the signature clause drawer.
// Summary register (calm, white) with the hero deadline; evidence register
// (verbatim, --document ground) grouped by purpose with server-resolved
// source locations. No plain-English explanations (that is Stage 4).
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { LegalFooter } from "@/components/cc/Primitives";

const PURPOSE_LABEL = {
  effective_date: "Effective date",
  renewal_term: "Renewal term",
  notice_period: "Notice period",
  notice_method: "Notice method",
  notice_recipient: "Notice recipient",
  business_day_definition: "Business day definition",
  deemed_receipt: "Deemed receipt",
  value: "Contract value",
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

export function FindingCard({ finding }) {
  const [open, setOpen] = useState(false);
  const e = finding.extracted || {};
  const t = tone(finding);
  const needsReview = finding.validation_status === "needs_review";

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
            <p className="cc-eyebrow">Automatic renewal</p>
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
            <p className="cc-eyebrow">Confidence</p>
            <p className={`cc-finding-title text-[16px] mt-1 capitalize ${TONE_TEXT[t]}`}
              data-testid="finding-confidence">{finding.confidence}</p>
          </div>
        </div>

        <div className={`mt-5 h-[3px] w-11 rounded ${TONE_RULE[t]}`} />

        {/* Key facts */}
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

        {finding.validation_notes?.length > 0 && (
          <ul className="mt-5 space-y-1">
            {finding.validation_notes.map((n, i) => (
              <li key={i} className="cc-days-remaining text-pending" data-testid="finding-note">• {n}</li>
            ))}
          </ul>
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
    </div>
  );
}

const Fact = ({ label, value, testid }) => (
  <div>
    <dt className="cc-eyebrow">{label}</dt>
    <dd className="cc-plain-english mt-1 text-ink" data-testid={testid}>{value}</dd>
  </div>
);
