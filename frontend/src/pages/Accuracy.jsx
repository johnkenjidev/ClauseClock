// /accuracy — internal operator instrumentation (PART 2). NOT a learning
// system; ClauseClock does not improve itself from corrections. Metrics are
// built in a later stage. Shell only.
import { Eyebrow, StageNote } from "@/components/cc/Primitives";
import { ACCURACY } from "@/constants/testIds";

export default function Accuracy() {
  return (
    <div
      data-testid={ACCURACY.root}
      className="min-h-screen bg-paper px-6 py-14"
    >
      <div className="mx-auto max-w-3xl">
        <Eyebrow>Internal · Accuracy</Eyebrow>
        <div className="cc-seal-rule mt-4 mb-6" />
        <h1 className="cc-finding-title text-2xl">Extraction accuracy</h1>
        <p className="cc-days-remaining mt-2 max-w-xl">
          Findings reviewed, confirmed unedited, corrected, and correction rate
          by finding type and field. Instrumentation for the operator — read
          these numbers and improve the extraction prompts.
        </p>
        <StageNote>
          Scaffold only. Accuracy metrics are computed in a later stage.
        </StageNote>
      </div>
    </div>
  );
}
