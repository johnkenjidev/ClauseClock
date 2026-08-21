// Action Center (Stage 6A) — confirmed, actionable renewal findings grouped by
// urgency. Opening one shows a Notice Checklist built only from validated
// contract sources, and can generate a grounded non-renewal draft. ClauseClock
// does NOT send anything; the user must verify and send it themselves.
import { useEffect, useState, useRef } from "react";
import { FileText, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
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

function LogActionForm({ findingId, contractMethod }) {
  const [form, setForm] = useState({ action_type: "notice_sent", sent_date: "", delivery_method: "", note: "" });
  const [actions, setActions] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const load = () => api.get(`/findings/${findingId}/actions`).then((r) => setActions(r.data.actions)).catch(() => {});
  useEffect(() => { load(); }, [findingId]);

  const save = async () => {
    setBusy(true); setErr("");
    try {
      await api.post(`/findings/${findingId}/actions`, form);
      setForm({ action_type: "notice_sent", sent_date: "", delivery_method: "", note: "" });
      load();
    } catch (e) { setErr(e.response?.data?.detail || "Could not save"); if (Array.isArray(e.response?.data?.detail)) setErr("Check the fields"); }
    finally { setBusy(false); }
  };

  return (
    <div className="pt-4 border-t border-rule" data-testid="log-action">
      <Eyebrow>Log an action</Eyebrow>
      <div className="grid grid-cols-2 gap-3 mt-3">
        <select data-testid="action-type" value={form.action_type} onChange={(e) => set("action_type", e.target.value)}
          className="bg-card border border-rule rounded-md h-9 px-2 cc-days-remaining">
          <option value="notice_sent">Notice sent</option>
          <option value="objection_sent">Objection sent</option>
          <option value="claim_submitted">Claim submitted</option>
          <option value="dispute_raised">Dispute raised</option>
        </select>
        <Input type="date" data-testid="action-sent-date" value={form.sent_date} onChange={(e) => set("sent_date", e.target.value)} className="bg-card border-rule h-9" />
        <Input data-testid="action-delivery-method" placeholder="Delivery method (e.g. certified mail)" value={form.delivery_method} onChange={(e) => set("delivery_method", e.target.value)} className="bg-card border-rule h-9 col-span-2" />
        <Input data-testid="action-note" placeholder="Optional note" value={form.note} onChange={(e) => set("note", e.target.value)} className="bg-card border-rule h-9 col-span-2" />
      </div>
      {err && <p className="cc-days-remaining text-stamp mt-2">{err}</p>}
      <Button onClick={save} disabled={busy || !form.sent_date || !form.delivery_method} data-testid="action-save"
        className="bg-ink text-paper hover:bg-ink/90 rounded-full h-9 px-5 mt-3">
        {busy ? "Saving…" : "Log action"}
      </Button>

      {actions.length > 0 && (
        <ul className="mt-4 space-y-2" data-testid="logged-actions">
          {actions.map((a) => (
            <li key={a.id} className="rounded-md border border-rule bg-card px-4 py-3">
              <p className="cc-finding-title text-[15px]">{a.action_type.replace(/_/g, " ")} · {a.sent_date}</p>
              <p className="cc-days-remaining mt-0.5">via {a.delivery_method}{a.note ? ` · ${a.note}` : ""}</p>
              {a.method_matches_contract === false && (
                <p className="cc-days-remaining text-stamp mt-1" data-testid="method-warning">
                  ⚠ The delivery method you logged differs from the contract-required method
                  {contractMethod ? ` (“${contractMethod}”)` : ""}. Double-check your contract before relying on this notice.
                </p>
              )}
              <EvidenceBlock action={a} onChanged={load} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;

function EvidenceBlock({ action, onChanged }) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);
  const files = action.evidence_files || [];

  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    try { await api.post(`/actions/${action.id}/evidence`, fd); onChanged?.(); }
    finally { setBusy(false); }
  };

  return (
    <div className="mt-3 pt-3 border-t border-rule" data-testid={`evidence-block-${action.id}`}>
      <div className="flex items-center justify-between">
        <span className="cc-eyebrow">Evidence of action</span>
        <button data-testid={`evidence-upload-btn-${action.id}`} disabled={busy}
          onClick={() => ref.current?.click()}
          className="cc-section-ref text-seal hover:underline">{busy ? "Uploading…" : "Attach evidence"}</button>
        <input ref={ref} type="file" className="hidden"
          data-testid={`evidence-input-${action.id}`}
          onChange={(e) => upload(e.target.files?.[0])} />
      </div>
      {files.length === 0 ? (
        <p className="cc-days-remaining mt-1 text-ink-soft">No evidence attached. This is a record of what you sent — not proof of valid notice.</p>
      ) : (
        <ul className="mt-2 space-y-1" data-testid={`evidence-list-${action.id}`}>
          {files.map((f, i) => (
            <li key={i} className="flex items-center justify-between rounded-md border border-rule bg-card px-3 py-2">
              <a href={`${API_BASE}/actions/${action.id}/evidence/${i}`} target="_blank" rel="noreferrer"
                className="cc-section-ref text-ink hover:text-seal">{f.filename}</a>
              <span className="cc-days-remaining">{(f.size_bytes / 1024).toFixed(0)} KB · SHA-256 {String(f.sha256).slice(0, 10)}… · {String(f.uploaded_at).slice(0, 10)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function OutcomeForm({ findingId }) {
  const [form, setForm] = useState({ result: "reviewed_and_kept", confirmed: false, amount_recovered: "", currency: "USD", notes: "" });
  const [outcomes, setOutcomes] = useState([]);
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const load = () => api.get(`/findings/${findingId}/outcomes`).then((r) => setOutcomes(r.data.outcomes)).catch(() => {});
  useEffect(() => { load(); }, [findingId]);

  const save = async () => {
    setBusy(true);
    const payload = { result: form.result, confirmed: form.confirmed, notes: form.notes || null,
      currency: form.currency || null,
      amount_recovered: form.amount_recovered ? parseFloat(form.amount_recovered) : null };
    try { await api.post(`/findings/${findingId}/outcomes`, payload); setForm({ result: "reviewed_and_kept", confirmed: false, amount_recovered: "", currency: "USD", notes: "" }); load(); }
    finally { setBusy(false); }
  };

  return (
    <div className="pt-4 border-t border-rule" data-testid="outcome-form">
      <Eyebrow>Record outcome</Eyebrow>
      <div className="grid grid-cols-2 gap-3 mt-3">
        <select data-testid="outcome-result" value={form.result} onChange={(e) => set("result", e.target.value)}
          className="bg-card border border-rule rounded-md h-9 px-2 cc-days-remaining col-span-2">
          {["terminated","renegotiated","credit_received","dispute_resolved","reviewed_and_kept","missed"].map((o) =>
            <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
        </select>
        <Input data-testid="outcome-amount" placeholder="Value (optional)" value={form.amount_recovered} onChange={(e) => set("amount_recovered", e.target.value)} className="bg-card border-rule h-9" />
        <Input data-testid="outcome-currency" placeholder="USD" value={form.currency} onChange={(e) => set("currency", e.target.value)} className="bg-card border-rule h-9" />
        <Input data-testid="outcome-notes" placeholder="Optional notes" value={form.notes} onChange={(e) => set("notes", e.target.value)} className="bg-card border-rule h-9 col-span-2" />
        <label className="flex items-center gap-2 cc-days-remaining col-span-2">
          <input type="checkbox" data-testid="outcome-confirmed" checked={form.confirmed} onChange={(e) => set("confirmed", e.target.checked)} /> Confirmed
        </label>
      </div>
      <Button onClick={save} disabled={busy} data-testid="outcome-save"
        className="bg-ink text-paper hover:bg-ink/90 rounded-full h-9 px-5 mt-3">{busy ? "Saving…" : "Record outcome"}</Button>
      {outcomes.length > 0 && (
        <ul className="mt-3 space-y-2" data-testid="outcome-list">
          {outcomes.map((o) => (
            <li key={o.id} className="rounded-md border border-rule bg-card px-4 py-2">
              <p className="cc-finding-title text-[15px]">{o.result.replace(/_/g, " ")}{o.confirmed ? " · confirmed" : ""}</p>
              <p className="cc-days-remaining mt-0.5">
                {o.amount_recovered != null ? `${o.currency || ""} ${o.amount_recovered}` : ""}{o.notes ? ` · ${o.notes}` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ChecklistPanel({ item }) {
  const [checklist, setChecklist] = useState(null);
  const [draft, setDraft] = useState(null);
  const [drafting, setDrafting] = useState(false);
  const isRenewal = item?.type === "renewal_notice";

  useEffect(() => {
    if (item && item.type === "renewal_notice") {
      setChecklist(null); setDraft(null);
      api.get(`/findings/${item.id}/checklist`).then((r) => setChecklist(r.data)).catch(() => {});
    } else {
      setChecklist(null); setDraft(null);
    }
  }, [item]);

  const generate = async () => {
    setDrafting(true);
    try {
      const { data } = await api.post(`/findings/${item.id}/draft-notice`);
      setDraft(data);
    } finally { setDrafting(false); }
  };

  if (!item) return (
    <div data-testid="checklist-empty" className="h-full flex items-center justify-center py-24">
      <p className="cc-days-remaining text-center max-w-xs">Select a finding from the queue to see what your contract requires, draft the notice, and log what you sent.</p>
    </div>
  );

  // Obligation finding types — reuse the same action workflow (log action,
  // record outcome, evidence) grounded in the finding's validated sources.
  // No renewal Notice Checklist / non-renewal draft (renewal-only).
  if (!isRenewal) {
    const e = item.extracted || {};
    return (
      <div data-testid="checklist-panel" className="pb-8">
        <p className="cc-finding-title">{item.contract_name} — {TYPE_LABEL[item.type] || "Action required"}</p>
        <div className="cc-seal-rule mt-3 mb-5" />
        <div className="mt-2 space-y-6">
          <div>
            <Eyebrow>Deadline</Eyebrow>
            <p className="cc-plain-english mt-1" data-testid="obligation-deadline">
              {longDate(e.effective_action_deadline)}
              {e.days_remaining != null ? ` · ${e.days_remaining} days remaining` : ""}
            </p>
          </div>
          {item.plain_english && (
            <div><Eyebrow>In plain English</Eyebrow>
              <p className="cc-plain-english mt-1" data-testid="obligation-plain-english">{item.plain_english}</p></div>
          )}
          {item.suggested_action && (
            <div><Eyebrow>Suggested action</Eyebrow>
              <p className="cc-plain-english mt-1">{item.suggested_action}</p></div>
          )}
          <div><Eyebrow>From the contract</Eyebrow>
            <Provenance sources={item.sources} /></div>
          <LogActionForm findingId={item.id} contractMethod={null} />
          <OutcomeForm findingId={item.id} />
        </div>
      </div>
    );
  }

  return (
    <div data-testid="checklist-panel" className="pb-8">
      <p className="cc-finding-title">{item.contract_name} — Notice checklist</p>
      <div className="cc-seal-rule mt-3 mb-5" />
        {!checklist ? <p className="cc-days-remaining mt-2">Loading…</p> : (
          <div className="mt-2 space-y-6">
            <div className="rounded-md border border-rule bg-card px-4 py-3 flex items-start gap-2">
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
                  <div className="rounded-md border border-rule bg-card px-4 py-3 mb-3 flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-pending mt-0.5" />
                    <p className="cc-days-remaining text-ink" data-testid="draft-disclaimer">{draft.disclaimer}</p>
                  </div>
                  <pre className="font-mono text-[13px] leading-[1.75] text-ink bg-card border border-rule rounded-md p-4 whitespace-pre-wrap" data-testid="draft-text">{draft.draft}</pre>
                </div>
              )}
            </div>

            <LogActionForm findingId={item.id} contractMethod={checklist.method.value} />
            <OutcomeForm findingId={item.id} />
          </div>
        )}
    </div>
  );
}

export default function ActionCenter() {
  const [data, setData] = useState(null);
  const [active, setActive] = useState(null);

  useEffect(() => { api.get("/action-center").then((r) => setData(r.data)).catch(() => setData({ buckets: {}, count: 0 })); }, []);

  return (
    <div data-testid={ACTION_CENTER.root}>
      <Eyebrow>Action Center</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-6" />
      <p className="cc-days-remaining mb-8 max-w-2xl">Confirmed findings with a deadline that need action — renewals to give notice on, plus claims, disputes and deadlines from your contracts. ClauseClock does not send anything — you review and act yourself.</p>

      {data === null && <p className="cc-days-remaining">Loading…</p>}
      {data && data.count === 0 && (
        <div className="rounded-lg border border-rule bg-card px-6 py-10 text-center">
          <p className="cc-plain-english text-ink-soft">No confirmed actions yet. Confirm an actionable finding with a deadline to see it here.</p>
        </div>
      )}

      {data && data.count > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-[38%_1fr] gap-0 border-t border-rule">
          {/* Master — prioritised queue (~38%) */}
          <div className="lg:border-r border-rule py-6 lg:pr-7">
            {BUCKETS.map(([key, label]) => {
              const items = data.buckets[key] || [];
              if (!items.length) return null;
              return (
                <div key={key} className="mb-6">
                  <Eyebrow>{label} · {items.length}</Eyebrow>
                  <ul className="mt-3 space-y-1">
                    {items.map((it) => {
                      const sel = active?.id === it.id;
                      const dr = it.extracted?.days_remaining;
                      const urgent = dr != null && dr <= 14;
                      return (
                        <li key={it.id}>
                          <button data-testid={`action-item-${it.id}`} onClick={() => setActive(it)}
                            className={`w-full rounded-md px-3 py-3 text-left transition-colors flex items-start gap-3 border ${sel ? "bg-card border-rule" : "border-transparent hover:bg-card"}`}>
                            <div className="w-16 shrink-0">
                              <p className={`text-[15px] font-semibold leading-none ${urgent ? "text-stamp" : ""}`}>{shortDate(it.extracted?.effective_action_deadline)}</p>
                              <p className={`text-[11.5px] mt-1 ${urgent ? "text-stamp" : "text-ink-soft"}`}>{dr != null ? `${dr} days` : "no date"}</p>
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
              );
            })}
          </div>

          {/* Detail — selected finding workflow (~62%) */}
          <div className="lg:pl-8 min-w-0">
            <ChecklistPanel item={active} />
          </div>
        </div>
      )}
    </div>
  );
}
