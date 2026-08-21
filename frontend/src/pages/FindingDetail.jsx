// Finding detail shell — PART 2 / 5.4. Progressive disclosure: plain English →
// why it matters → suggested action → original clause (the clause drawer).
// This renders the *structure* only; no extracted data or explanations exist
// until later stages, so the drawer stays closed and empty.
import { Eyebrow, StageNote, LegalFooter } from "@/components/cc/Primitives";
import { FINDING_DETAIL } from "@/constants/testIds";

export default function FindingDetail() {
  return (
    <div data-testid={FINDING_DETAIL.root} className="max-w-2xl">
      <Eyebrow>Finding</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-6" />

      {/* Summary register — calm and human (white surface) */}
      <div className="rounded-lg border border-rule bg-card p-6">
        <p className="cc-finding-title text-ink-soft">
          Plain English summary renders here.
        </p>
        <p className="cc-plain-english mt-4 text-ink-soft">
          Why it matters, then a suggested action, follow beneath — each
          generated from validated clause quotes in a later stage.
        </p>

        {/* Evidence register — verbatim and documentary (--document ground) */}
        <div className="mt-6 rounded-md border border-rule bg-card p-5">
          <p className="cc-section-ref">Show the contract language ⌄</p>
          <p className="cc-clause mt-3 text-ink-soft">
            Verbatim clause quotes, grouped by purpose with their section
            reference and page, appear here once analysis runs.
          </p>
        </div>

        <div className="mt-6 pt-5 border-t border-rule">
          <LegalFooter />
        </div>
      </div>

      <StageNote>
        Scaffold only. Confirm / Correct / Dismiss controls, confidence, the
        opening clause drawer and generated explanations arrive in later stages.
      </StageNote>
    </div>
  );
}
