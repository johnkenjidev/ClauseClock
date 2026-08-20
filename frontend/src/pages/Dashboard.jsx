// Dashboard shell — /app for a new user with no contracts shows the empty
// state (PART 5.5). Dashboard figures/logic are Stage-later and NOT built.
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Eyebrow, StageNote } from "@/components/cc/Primitives";
import { DASHBOARD } from "@/constants/testIds";

export default function Dashboard() {
  const navigate = useNavigate();
  return (
    <div data-testid={DASHBOARD.root} className="max-w-2xl">
      <Eyebrow>Your workspace</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-6" />

      <h1 className="font-archivo font-semibold text-ink text-3xl sm:text-4xl leading-tight tracking-tight">
        Add a contract and ClauseClock finds the
        <br className="hidden sm:block" /> deadlines that cost money.
      </h1>

      <div className="mt-8 flex flex-wrap gap-3">
        <Button
          data-testid={DASHBOARD.emptyAddContract}
          onClick={() => navigate("/app/upload")}
          className="bg-ink text-paper hover:bg-ink/90 rounded-full h-11 px-6"
        >
          Add a contract
        </Button>
        <Button
          variant="outline"
          data-testid={DASHBOARD.emptySample}
          onClick={() => navigate("/demo")}
          className="rounded-full h-11 px-6 border-rule text-ink hover:bg-document"
        >
          See a sample workspace
        </Button>
      </div>

      <StageNote>
        Scaffold only. Dashboard figures — contracts monitored, value under
        tracking, confirmed value protected, windows missed — arrive in a later
        stage. No dashboard logic has been implemented yet.
      </StageNote>
    </div>
  );
}
