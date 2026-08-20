// /accuracy — internal operator instrumentation (Stage 3). Reads stored
// finding data only. NOT a learning system; ClauseClock does not improve
// itself from these numbers — they are for the operator to read.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Eyebrow } from "@/components/cc/Primitives";
import { ACCURACY } from "@/constants/testIds";

const Stat = ({ label, value, testid }) => (
  <div className="rounded-lg border border-rule bg-card px-6 py-5">
    <p className="cc-eyebrow">{label}</p>
    <p className="cc-hero-date text-ink mt-2 text-[40px]" data-testid={testid}>{value}</p>
  </div>
);

export default function Accuracy() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/accuracy").then((r) => setData(r.data))
      .catch(() => setError("Sign in to view accuracy instrumentation."));
  }, []);

  return (
    <div data-testid={ACCURACY.root} className="min-h-screen bg-paper px-6 py-14">
      <div className="mx-auto max-w-3xl">
        <Eyebrow>Internal · Accuracy</Eyebrow>
        <div className="cc-seal-rule mt-4 mb-6" />
        <h1 className="cc-finding-title text-2xl">Extraction accuracy</h1>
        <p className="cc-days-remaining mt-2 max-w-xl">
          Operator instrumentation over stored findings — read these to improve
          the extraction prompts. This is not a self-learning system.
        </p>

        {error && <p className="cc-days-remaining text-stamp mt-8" data-testid="accuracy-error">{error}</p>}

        {data && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8">
              <Stat label="Reviewed" value={data.findings_reviewed} testid="accuracy-reviewed" />
              <Stat label="Confirmed" value={data.confirmed_no_edits} testid="accuracy-confirmed" />
              <Stat label="Corrected" value={data.corrected} testid="accuracy-corrected" />
              <Stat label="Correction rate" value={`${data.correction_rate_pct}%`} testid="accuracy-rate" />
            </div>

            <div className="mt-10">
              <Eyebrow>Corrected-field frequency</Eyebrow>
              <div className="cc-seal-rule mt-3 mb-4" />
              {Object.keys(data.corrected_field_frequency).length === 0 ? (
                <p className="cc-days-remaining">No corrections recorded yet.</p>
              ) : (
                <ul className="divide-y divide-rule rounded-lg border border-rule bg-card" data-testid="accuracy-field-freq">
                  {Object.entries(data.corrected_field_frequency).map(([f, n]) => (
                    <li key={f} className="flex items-center justify-between px-5 py-3">
                      <span className="cc-section-ref">{f}</span>
                      <span className="cc-money">{n}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="mt-10">
              <Eyebrow>By finding type</Eyebrow>
              <div className="cc-seal-rule mt-3 mb-4" />
              <ul className="divide-y divide-rule rounded-lg border border-rule bg-card" data-testid="accuracy-by-type">
                {Object.entries(data.by_type).map(([type, s]) => (
                  <li key={type} className="px-5 py-4">
                    <p className="cc-finding-title text-[16px]">{type}</p>
                    <p className="cc-days-remaining mt-1">
                      reviewed {s.reviewed} · confirmed {s.confirmed_no_edits} · corrected {s.corrected}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
