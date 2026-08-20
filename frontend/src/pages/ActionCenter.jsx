// Action Center (Stage 6A) — confirmed, actionable renewal findings grouped by
// urgency. Opening one shows a Notice Checklist built only from validated
// contract sources, and can generate a grounded non-renewal draft. ClauseClock
// does NOT send anything; the user must verify and send it themselves.
import { useEffect, useState } from "react";
import { FileText, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { Eyebrow } from "@/components/cc/Primitives";
import { ACTION_CENTER } from "@/constants/testIds";

const BUCKETS = [
  ["urgent", "Urgent · within 14 days"],
  ["next_30_days", "Next 30 days"],
  ["later", "Later"],
];

const longDate = (iso) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
};

function Provenance({ sources }) {
  if (!sources?.length) return null;
  return (
    <div className="mt-2 space-y-2">
      {sources.map((s, i) => (
        <div key={i} className="rounded-md border border-rule bg-document p-3">
          <span className="cc-section-ref">{s.location}</span>
          <p className="cc-clause mt-1 text-ink">&ldquo;{s.quote}&rdquo;</p>
        </div>
      ))}
    </div>
  );
}

function ChecklistDialog({ item, open, onOpenChange }) {
  const [checklist, setChecklist] = useState(null);
  const [draft, setDraft] = useState(null);
  const [drafting, setDrafting] = useState(false);

  useEffect(() => {
    if (open && item) {
      setChecklist(null); setDraft(null);
      api.get(`/findings/${item.id}/checklist`).then((r) => setChecklist(r.data)).catch(() => {});
    }
  }, [open, item]);

  const generate = async () => {
    setDrafting(true);
    try {
      const { data } = await api.post(`/findings/${item.id}/draft-notice`);
      setDraft(data);
    } finally { setDrafting(false); }
  };

  if (!item) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="checklist-dialog" className="max-w-2xl max-h-[85vh] overflow-y-auto bg-paper">
        <DialogHeader><DialogTitle className="cc-finding-title">{item.contract_name} — Notice checklist</DialogTitle></DialogHeader>

        {!checklist ? <p className="cc-days-remaining mt-2">Loading…</p> : (
          <div className="mt-2 space-y-6">
            <div className="rounded-md border border-rule bg-document px-4 py-3 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-pending mt-0.5" />
              <p className="cc-days-remaining text-ink" data-testid="checklist-disclaimer">{checklist.disclaimer}</p>
            </div>

            <div><Eyebrow>Required method</Eyebrow>
              <p className="cc-plain-english mt-1">{checklist.method.value || "Not stated in contract"}</p>
              <Provenance sources={checklist.method.sources} /></div>

            <div><Eyebrow>Recipient / address</Eyebrow>
              <p className="cc-plain-english mt-1">{checklist.recipient.value || "Not stated in contract"}</p>
              <Provenance sources={checklist.recipient.sources} /></div>

            <div><Eyebrow>Timing</Eyebrow>
              <p className="cc-plain-english mt-1">
                {checklist.timing.notice_days_min} {checklist.timing.notice_basis || "calendar"} days before {longDate(checklist.timing.next_renewal_date)} · deadline {longDate(checklist.timing.action_deadline)}
              </p>
              <Provenance sources={checklist.timing.sources} /></div>

            <div><Eyebrow>Renewal term</Eyebrow><Provenance sources={checklist.renewal_term.sources} /></div>

            <div className="pt-2 border-t border-rule">
              <Button onClick={generate} disabled={drafting} data-testid="generate-draft-btn"
                className="bg-ink text-paper hover:bg-ink/90 rounded-full h-10 px-5">
                {drafting ? "Drafting…" : "Generate non-renewal draft"}
              </Button>

              {draft && (
                <div className="mt-4" data-testid="notice-draft">
                  <div className="rounded-md border border-rule bg-document px-4 py-3 mb-3 flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-pending mt-0.5" />
                    <p className="cc-days-remaining text-ink" data-testid="draft-disclaimer">{draft.disclaimer}</p>
                  </div>
                  <pre className="cc-clause bg-card border border-rule rounded-md p-4 whitespace-pre-wrap">{draft.draft}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function ActionCenter() {
  const [data, setData] = useState(null);
  const [active, setActive] = useState(null);

  useEffect(() => { api.get("/action-center").then((r) => setData(r.data)).catch(() => setData({ buckets: {}, count: 0 })); }, []);

  return (
    <div data-testid={ACTION_CENTER.root} className="max-w-3xl">
      <Eyebrow>Action Center</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-6" />
      <p className="cc-days-remaining mb-8">Confirmed renewals that need a notice. ClauseClock does not send notices — you review and send them yourself.</p>

      {data === null && <p className="cc-days-remaining">Loading…</p>}
      {data && data.count === 0 && (
        <div className="rounded-lg border border-rule bg-card px-6 py-10 text-center">
          <p className="cc-plain-english text-ink-soft">No confirmed renewal actions yet. Confirm an automatic-renewal finding to see it here.</p>
        </div>
      )}

      {data && data.count > 0 && (
        <div className="space-y-6">
          {BUCKETS.map(([key, label]) => {
            const items = data.buckets[key] || [];
            if (!items.length) return null;
            return (
              <div key={key}>
                <Eyebrow>{label}</Eyebrow>
                <ul className="mt-3 space-y-3">
                  {items.map((it) => (
                    <li key={it.id}>
                      <button data-testid={`action-item-${it.id}`} onClick={() => { setActive(it); }}
                        className="w-full rounded-lg border border-rule bg-card px-5 py-4 text-left hover:bg-document/50 transition-colors flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <FileText className="h-5 w-5 text-ink-soft" />
                          <div>
                            <p className="cc-finding-title text-[16px]">{it.contract_name}</p>
                            <p className="cc-days-remaining mt-0.5">
                              {(it.extracted?.days_remaining ?? "—")} days · deadline {longDate(it.extracted?.effective_action_deadline)}
                            </p>
                          </div>
                        </div>
                        <span className="cc-section-ref">Open checklist</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}

      <ChecklistDialog item={active} open={!!active} onOpenChange={(v) => !v && setActive(null)} />
    </div>
  );
}
