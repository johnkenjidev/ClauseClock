// Contracts shell — empty list state. Contract listing/logic is a later stage.
import { useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Eyebrow, StageNote } from "@/components/cc/Primitives";
import { CONTRACTS } from "@/constants/testIds";

export default function Contracts() {
  const navigate = useNavigate();
  return (
    <div data-testid={CONTRACTS.root}>
      <Eyebrow>Contracts</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-8" />

      <div className="rounded-lg border border-rule bg-card px-8 py-16 flex flex-col items-center text-center">
        <div className="h-12 w-12 rounded-full bg-document flex items-center justify-center">
          <FileText className="h-6 w-6 text-ink-soft" strokeWidth={1.75} />
        </div>
        <p className="cc-plain-english mt-5 max-w-sm">
          No contracts yet. Add one and ClauseClock reads the paper so you
          don&rsquo;t have to.
        </p>
        <Button
          data-testid={CONTRACTS.emptyAddContract}
          onClick={() => navigate("/app/upload")}
          className="mt-6 bg-ink text-paper hover:bg-ink/90 rounded-full h-11 px-6"
        >
          Add a contract
        </Button>
      </div>

      <StageNote>
        Scaffold only. The ranked What Matters list, findings and clause drawers
        are built in later stages.
      </StageNote>
    </div>
  );
}
