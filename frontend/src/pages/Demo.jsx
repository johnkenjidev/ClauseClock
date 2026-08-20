// /demo — PART 5.9. No auth, no signup wall, read-only. Opens into the shell
// of a populated synthetic workspace. Synthetic data generation and the
// floating date anchor are explicitly a LATER stage — not built here.
import { Eyebrow, StageNote } from "@/components/cc/Primitives";
import { DEMO } from "@/constants/testIds";

export default function Demo() {
  return (
    <div data-testid={DEMO.root} className="max-w-2xl">
      <Eyebrow>Overview</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-6" />

      <h1 className="font-archivo font-semibold text-ink text-2xl sm:text-3xl leading-tight">
        Nothing buried. This is where the sample workspace opens.
      </h1>
      <p className="cc-plain-english mt-4 text-ink-soft">
        The submitted demo opens on the portfolio as it looks three months into
        use — most contracts calm, one thing needing action — never on an upload
        box. Read-only, synthetic data only.
      </p>

      <StageNote>
        Scaffold only. Synthetic contracts, synthetic evidence and the floating
        &ldquo;demo_today&rdquo; date anchor are built in a later stage. No demo
        functionality has been implemented yet.
      </StageNote>
    </div>
  );
}
