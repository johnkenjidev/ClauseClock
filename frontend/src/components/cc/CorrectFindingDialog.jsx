// Correct dialog — edit the existing extracted renewal fields (Stage 3).
// Empty inputs are sent as null (allows supplying a previously missing
// effective_date). No LLM is rerun; the server recomputes dates deterministically.
import { useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api, formatApiErrorDetail } from "@/lib/api";

const NUM = ["initial_term_value", "renewal_period_value", "notice_days_min", "notice_days_max"];
const PRICE_INT = ["objection_window_value"];
const PRICE_FLOAT = ["increase_percent", "increase_amount"];

const RENEWAL_FIELDS = [
  "effective_date", "initial_term_value", "initial_term_unit", "renewal_type",
  "renewal_period_value", "renewal_period_unit", "notice_days_min",
  "notice_days_max", "notice_basis", "business_day_definition",
  "notice_measured_to", "deemed_receipt_rule", "notice_method", "notice_recipient",
];
const PRICE_FIELDS = [
  "increase_type", "increase_percent", "increase_amount", "increase_formula",
  "increase_basis", "price_change_date", "objection_window_value",
  "objection_window_unit", "objection_basis", "objection_measured_to",
  "objection_deadline_stated", "objection_recipient", "objection_method",
];

const emptyToNull = (v) => (v === "" || v === undefined ? null : v);

export function CorrectFindingDialog({ finding, open, onOpenChange, onSaved }) {
  const isPrice = finding.type === "price_increase";
  const e = finding.extracted || {};
  const init = {};
  (isPrice ? PRICE_FIELDS : RENEWAL_FIELDS).forEach((k) => (init[k] = e[k] ?? ""));
  const [form, setForm] = useState(init);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    setBusy(true); setError("");
    const payload = {};
    Object.entries(form).forEach(([k, v]) => {
      let val = emptyToNull(v);
      if (NUM.includes(k) && val !== null) val = parseInt(val, 10);
      if (PRICE_INT.includes(k) && val !== null) val = parseInt(val, 10);
      if (PRICE_FLOAT.includes(k) && val !== null) val = parseFloat(val);
      payload[k] = val;
    });
    try {
      const { data } = await api.post(`/findings/${finding.id}/correct`, payload);
      onSaved(data.finding);
      onOpenChange(false);
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally { setBusy(false); }
  };

  const Sel = ({ k, label, options }) => (
    <div className="space-y-1.5">
      <Label className="cc-eyebrow">{label}</Label>
      <Select value={form[k] || "__null"} onValueChange={(v) => set(k, v === "__null" ? "" : v)}>
        <SelectTrigger data-testid={`correct-field-${k}`} className="bg-card border-rule h-9"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="__null">—</SelectItem>
          {options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  );
  const Txt = ({ k, label, ph, type = "text" }) => (
    <div className="space-y-1.5">
      <Label className="cc-eyebrow">{label}</Label>
      <Input type={type} value={form[k]} placeholder={ph}
        data-testid={`correct-field-${k}`} onChange={(ev) => set(k, ev.target.value)}
        className="bg-card border-rule h-9" />
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="correct-dialog" className="max-w-2xl max-h-[85vh] overflow-y-auto bg-paper">
        <DialogHeader>
          <DialogTitle className="cc-finding-title">Correct this finding</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
          {isPrice ? (
            <>
              <Sel k="increase_type" label="Increase type"
                options={["fixed_automatic", "capped", "formula", "unspecified"]} />
              <Txt k="increase_percent" label="Increase percent (max, if capped)" ph="3" type="number" />
              <Txt k="increase_amount" label="Increase amount" ph="500" type="number" />
              <Txt k="increase_formula" label="Formula / index" ph="CPI + 2%" />
              <Txt k="increase_basis" label="Applies to" ph="annual fees" />
              <Txt k="price_change_date" label="Effective from (YYYY-MM-DD)" ph="2026-01-01" />
              <Txt k="objection_window_value" label="Objection window value" ph="30" type="number" />
              <Sel k="objection_window_unit" label="Objection window unit" options={["days", "months", "years"]} />
              <Sel k="objection_basis" label="Objection basis" options={["calendar", "business"]} />
              <Sel k="objection_measured_to" label="Measured to" options={["sent", "received", "unspecified"]} />
              <Txt k="objection_deadline_stated" label="Objection deadline (YYYY-MM-DD)" ph="optional" />
              <Txt k="objection_recipient" label="Objection recipient" ph="Account Manager" />
              <Txt k="objection_method" label="Objection method" ph="written notice" />
            </>
          ) : (
            <>
              <Txt k="effective_date" label="Effective date (YYYY-MM-DD)" ph="2025-03-01" />
              <Sel k="renewal_type" label="Renewal type" options={["automatic", "manual", "none"]} />
              <Txt k="initial_term_value" label="Initial term value" ph="12" type="number" />
              <Sel k="initial_term_unit" label="Initial term unit" options={["days", "months", "years"]} />
              <Txt k="renewal_period_value" label="Renewal period value" ph="12" type="number" />
              <Sel k="renewal_period_unit" label="Renewal period unit" options={["days", "months", "years"]} />
              <Txt k="notice_days_min" label="Notice days (min)" ph="60" type="number" />
              <Txt k="notice_days_max" label="Notice days (max)" ph="90" type="number" />
              <Sel k="notice_basis" label="Notice basis" options={["calendar", "business"]} />
              <Sel k="notice_measured_to" label="Measured to" options={["sent", "received", "unspecified"]} />
              <Txt k="business_day_definition" label="Business day definition" ph="optional" />
              <Txt k="deemed_receipt_rule" label="Deemed receipt rule" ph="optional" />
              <Txt k="notice_method" label="Notice method" ph="certified mail" />
              <Txt k="notice_recipient" label="Notice recipient" ph="General Counsel" />
            </>
          )}
        </div>

        {error && <p className="cc-days-remaining text-stamp mt-2" data-testid="correct-error">{error}</p>}

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-full border-rule">Cancel</Button>
          <Button onClick={save} disabled={busy} data-testid="correct-save"
            className="bg-ink text-paper hover:bg-ink/90 rounded-full">
            {busy ? "Saving…" : "Save corrections"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
