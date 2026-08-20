// Upload — real Add contract flow (Stage 1). Uploads a PDF/DOCX with name,
// counterparty, document role, and optional annual value + currency.
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, FileText } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api, formatApiErrorDetail } from "@/lib/api";
import { Eyebrow } from "@/components/cc/Primitives";
import { UPLOAD } from "@/constants/testIds";

const DOC_ROLES = [
  ["primary", "Primary agreement"],
  ["amendment", "Amendment"],
  ["order_form", "Order form"],
  ["exhibit", "Exhibit"],
  ["sla", "SLA"],
];

export default function Upload() {
  const navigate = useNavigate();
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [counterparty, setCounterparty] = useState("");
  const [docRole, setDocRole] = useState("primary");
  const [annualValue, setAnnualValue] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const pickFile = (f) => {
    if (!f) return;
    const ok = /\.(pdf|docx)$/i.test(f.name);
    if (!ok) { setError("Only PDF and DOCX files are supported."); return; }
    setError("");
    setFile(f);
    if (!name) setName(f.name.replace(/\.(pdf|docx)$/i, ""));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!file) { setError("Choose a PDF or DOCX file first."); return; }
    if (!name.trim()) { setError("Give the contract a name."); return; }
    setBusy(true);
    setError("");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name.trim());
    fd.append("counterparty", counterparty.trim());
    fd.append("doc_role", docRole);
    if (annualValue.trim()) {
      fd.append("annual_value", annualValue.trim());
      fd.append("currency", currency);
    }
    try {
      const { data } = await api.post("/contracts", fd);
      navigate(`/app/contracts/${data.contract.id}`);
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid={UPLOAD.root} className="max-w-xl">
      <Eyebrow>Add a contract</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-8" />

      <form onSubmit={submit} className="space-y-6">
        <div
          data-testid="upload-dropzone"
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault(); setDragging(false);
            pickFile(e.dataTransfer.files?.[0]);
          }}
          className={`rounded-lg border-2 border-dashed px-8 py-12 flex flex-col items-center text-center cursor-pointer transition-colors duration-150 ${
            dragging ? "border-seal bg-document" : "border-rule bg-card hover:bg-document/60"
          }`}
        >
          {file ? (
            <>
              <FileText className="h-8 w-8 text-seal" strokeWidth={1.75} />
              <p className="cc-plain-english mt-3">{file.name}</p>
              <p className="cc-days-remaining mt-1">Click to choose a different file</p>
            </>
          ) : (
            <>
              <UploadCloud className="h-8 w-8 text-ink-soft" strokeWidth={1.75} />
              <p className="cc-plain-english mt-3">Drag and drop a PDF or DOCX, or click to browse.</p>
              <p className="cc-days-remaining mt-1">Text-based documents only.</p>
            </>
          )}
          <input
            ref={fileRef} type="file" accept=".pdf,.docx" className="hidden"
            data-testid="upload-file-input"
            onChange={(e) => pickFile(e.target.files?.[0])}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="name" className="cc-eyebrow">Contract name</Label>
          <Input id="name" value={name} data-testid="upload-name"
            onChange={(e) => setName(e.target.value)} className="bg-card border-rule" />
        </div>

        <div className="space-y-2">
          <Label htmlFor="counterparty" className="cc-eyebrow">Counterparty</Label>
          <Input id="counterparty" value={counterparty} data-testid="upload-counterparty"
            onChange={(e) => setCounterparty(e.target.value)} className="bg-card border-rule"
            placeholder="e.g. Acme Corp" />
        </div>

        <div className="space-y-2">
          <Label className="cc-eyebrow">Document role</Label>
          <Select value={docRole} onValueChange={setDocRole}>
            <SelectTrigger data-testid="upload-doc-role" className="bg-card border-rule">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DOC_ROLES.map(([v, label]) => (
                <SelectItem key={v} value={v} data-testid={`upload-doc-role-${v}`}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 space-y-2">
            <Label htmlFor="annual-value" className="cc-eyebrow">Annual value (optional)</Label>
            <Input id="annual-value" value={annualValue} data-testid="upload-annual-value"
              onChange={(e) => setAnnualValue(e.target.value)} className="bg-card border-rule cc-money"
              placeholder="24000" inputMode="decimal" />
          </div>
          <div className="space-y-2">
            <Label className="cc-eyebrow">Currency</Label>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger data-testid="upload-currency" className="bg-card border-rule">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["USD", "EUR", "GBP", "INR", "AUD", "CAD"].map((c) => (
                  <SelectItem key={c} value={c}>{c}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {error && <p data-testid="upload-error" className="cc-days-remaining text-stamp">{error}</p>}

        <Button type="submit" disabled={busy} data-testid="upload-submit"
          className="bg-ink text-paper hover:bg-ink/90 rounded-full h-11 px-6">
          {busy ? "Reading the paper…" : "Add contract"}
        </Button>
      </form>
    </div>
  );
}
