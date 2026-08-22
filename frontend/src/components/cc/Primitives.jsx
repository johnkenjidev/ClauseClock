// Small shared presentational primitives for the ClauseClock shells (PART 5).
// No data logic — Stage 1+ behaviour is intentionally absent.
import { cn } from "@/lib/utils";

export const Eyebrow = ({ children, className }) => (
  <p className={cn("cc-eyebrow", className)}>{children}</p>
);

// The scaffold notice shown on shells that will gain behaviour in later stages.
export const StageNote = ({ children }) => (
  <div className="mt-8 inline-flex items-start gap-2 rounded-md border border-rule bg-card px-4 py-3">
    <span className="cc-section-ref mt-0.5">§0</span>
    <p className="cc-days-remaining max-w-md text-left">{children}</p>
  </div>
);

// Global finding footer copy (PART 1.8) — the disclaimer that belongs beneath
// findings once they exist.
export const LegalFooter = ({ className }) => (
  <p
    className={cn("cc-days-remaining text-[13px] leading-relaxed", className)}
    data-testid="legal-disclaimer-footer"
  >
    ClauseClock identifies possible obligations and rights from your documents.
    Verify against the original contract before acting. This is not legal advice.
  </p>
);

// Reusable, reason-driven finding banner. Neutral/informational by default so
// it never reads like an urgent deadline or an error. Accepts a message so the
// same component can later render other refusal/verification reasons (missing
// effective date, unknown notice anchor, ...) — pass the reason text in.
const BANNER_TONE = {
  info: "border-rule bg-card text-ink-soft",
  warn: "border-pending/40 bg-card text-pending",
};
export const FindingBanner = ({ message, tone = "info", testid = "finding-banner" }) => (
  <div
    data-testid={testid}
    className={cn("mt-4 flex items-start gap-2 rounded-md border px-4 py-3",
      BANNER_TONE[tone] || BANNER_TONE.info)}
  >
    <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-current opacity-60" />
    <p className="cc-days-remaining text-left">{message}</p>
  </div>
);
