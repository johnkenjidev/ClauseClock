// Action Center shell — PART 2 / 5.6: an inbox with Urgent / Next 30 days /
// Later / Completed. No cross-contract window logic or drafting (later stage).
import { Eyebrow, StageNote } from "@/components/cc/Primitives";
import { ACTION_CENTER } from "@/constants/testIds";

const BUCKETS = ["Urgent", "Next 30 days", "Later", "Completed"];

export default function ActionCenter() {
  return (
    <div data-testid={ACTION_CENTER.root} className="max-w-3xl">
      <Eyebrow>Action Center</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-8" />

      <div className="space-y-4">
        {BUCKETS.map((bucket) => (
          <div
            key={bucket}
            className="rounded-lg border border-rule bg-card px-6 py-5"
          >
            <Eyebrow>{bucket}</Eyebrow>
            <p className="cc-days-remaining mt-2">Nothing here yet.</p>
          </div>
        ))}
      </div>

      <StageNote>
        Scaffold only. Open windows across all contracts, draft generation,
        action logging and evidence upload are built in later stages.
      </StageNote>
    </div>
  );
}
