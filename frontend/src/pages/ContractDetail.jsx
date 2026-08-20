// Contract detail shell — PART 2 structure: title, page count, annual value
// with provenance link, then the What Matters list. No findings logic yet.
import { Eyebrow, StageNote } from "@/components/cc/Primitives";
import { CONTRACT_DETAIL } from "@/constants/testIds";

export default function ContractDetail() {
  return (
    <div data-testid={CONTRACT_DETAIL.root} className="max-w-3xl">
      <Eyebrow>Contract</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-6" />

      <h1 className="cc-finding-title text-2xl">Contract detail</h1>
      <p className="cc-days-remaining mt-2">
        Title, page count and annual value with its own provenance link, then
        the ranked What Matters list, will render here.
      </p>

      <div className="mt-8 rounded-lg border border-rule bg-card p-6">
        <Eyebrow>What matters</Eyebrow>
        <p className="cc-plain-english mt-3 text-ink-soft">
          Findings ranked by score, coloured by category, each opening its
          clause drawer — built in a later stage.
        </p>
      </div>

      <StageNote>
        Scaffold only. Document list, amendment warning, findings and the clause
        drawer are not implemented yet.
      </StageNote>
    </div>
  );
}
