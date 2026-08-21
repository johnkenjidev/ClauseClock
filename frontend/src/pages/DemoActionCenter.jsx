import { useMemo, useState } from "react";
import { Eyebrow } from "@/components/cc/Primitives";
import { buildDemoWorkspace } from "@/data/demoWorkspace";

const TYPE_LABEL = {
  renewal_notice: "Automatic renewal · notice required",
  termination_right: "Termination right · notice",
  price_increase: "Price increase · objection",
  service_credit: "Service credit · claim",
  invoice_dispute: "Invoice dispute · deadline",
  warranty_claim: "Warranty claim · deadline",
  rebate_or_refund: "Rebate / refund · claim",
  fee_or_penalty: "Fee / penalty · deadline",
  notice_requirement: "Notice requirement · deadline",
};

const longDate = (iso) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });
};

const shortDate = (iso) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

function Provenance({ sources }) {
  if (!sources?.length) return null;
  return (
    <div className="mt-2 space-y-2">
      {sources.map((s, i) => (
        <div key={i} className="rounded-md border border-document-rule bg-document p-3">
          <span className="cc-section-ref">{s.location}</span>
          <p className="cc-clause mt-1">{s.quote}</p>
        </div>
      ))}
    </div>
  );
}

export default function DemoActionCenter() {
  const { actionItems } = useMemo(() => buildDemoWorkspace(new Date()), []);
  const [active, setActive] = useState(actionItems[0] || null);

  return (
    <div data-testid="demo-action-center">
      <div className="flex items-center justify-between gap-4">
        <Eyebrow>Action Center</Eyebrow>
        <span className="cc-eyebrow px-3 py-1 rounded-full bg-card border border-rule text-ink-soft">
          Synthetic demo · read-only
        </span>
      </div>
      <div className="cc-seal-rule mt-4 mb-6" />
      <p className="cc-days-remaining mb-8 max-w-2xl">
        Confirmed findings with a real deadline move here so you can see what the contract requires, act, preserve evidence, and record the outcome. This demo is read-only.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-[38%_1fr] gap-0 border-t border-rule">
        <div className="lg:border-r border-rule py-6 lg:pr-7">
          <Eyebrow>Prioritized queue · {actionItems.length}</Eyebrow>
          <ul className="mt-3 space-y-1">
            {actionItems.map((it) => {
              const selected = active?.id === it.id;
              const days = it.extracted?.days_remaining;
              const urgent = days != null && days <= 14;
              return (
                <li key={it.id}>
                  <button
                    onClick={() => setActive(it)}
                    className={`w-full rounded-md px-3 py-3 text-left transition-colors flex items-start gap-3 border ${selected ? "bg-card border-rule" : "border-transparent hover:bg-card"}`}
                  >
                    <div className="w-16 shrink-0">
                      <p className={`text-[15px] font-semibold leading-none ${urgent ? "text-stamp" : ""}`}>
                        {shortDate(it.extracted?.effective_action_deadline)}
                      </p>
                      <p className={`text-[11.5px] mt-1 ${urgent ? "text-stamp" : "text-ink-soft"}`}>
                        {days != null ? `${days} days` : "no date"}
                      </p>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-[14px] font-semibold truncate">{it.contract_name}</p>
                      <p className="text-[12.5px] text-ink-soft truncate">{TYPE_LABEL[it.type] || "Action required"}</p>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="lg:pl-8 min-w-0 py-6">
          {!active ? (
            <p className="cc-days-remaining">No demo actions.</p>
          ) : (
            <div className="pb-8">
              <p className="cc-finding-title">{active.contract_name} — {TYPE_LABEL[active.type] || "Action required"}</p>
              <div className="cc-seal-rule mt-3 mb-5" />

              <div className="space-y-6">
                <div>
                  <Eyebrow>Deadline</Eyebrow>
                  <p className="cc-plain-english mt-1">
                    {longDate(active.extracted?.effective_action_deadline)}
                    {active.extracted?.days_remaining != null ? ` · ${active.extracted.days_remaining} days remaining` : ""}
                  </p>
                </div>

                {active.plain_english && (
                  <div>
                    <Eyebrow>In plain English</Eyebrow>
                    <p className="cc-plain-english mt-1">{active.plain_english}</p>
                  </div>
                )}

                {active.suggested_action && (
                  <div>
                    <Eyebrow>Suggested action</Eyebrow>
                    <p className="cc-plain-english mt-1">{active.suggested_action}</p>
                  </div>
                )}

                <div>
                  <Eyebrow>From the contract</Eyebrow>
                  <Provenance sources={active.sources} />
                </div>

                <div className="pt-4 border-t border-rule">
                  <Eyebrow>What happens next in the real workspace</Eyebrow>
                  <ol className="mt-3 space-y-2 cc-plain-english text-ink-soft">
                    <li>1. Review the source clause and required method.</li>
                    <li>2. Log the notice, objection, claim, or dispute you sent.</li>
                    <li>3. Attach evidence such as the sent notice or confirmation.</li>
                    <li>4. Record the outcome and value protected or recovered.</li>
                  </ol>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
