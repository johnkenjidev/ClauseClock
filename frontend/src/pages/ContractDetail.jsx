// Contract detail — Stage 1. Shows name, counterparty, annual value with its
// provenance, the uploaded document list with roles, and the extracted text
// with location markers (inspectable, for extraction-quality testing).
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Trash2, FileText, AlertTriangle, ScanSearch, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { api } from "@/lib/api";
import { Eyebrow } from "@/components/cc/Primitives";
import { FindingCard } from "@/components/cc/FindingCard";
import { CONTRACT_DETAIL, TIMELINE } from "@/constants/testIds";

const money = (v, cur) =>
  v == null ? null : new Intl.NumberFormat("en-US", {
    style: "currency", currency: cur || "USD", maximumFractionDigits: 0,
  }).format(v);

const KIND_LABEL = { finding: "Finding", action: "Action", evidence: "Evidence", outcome: "Outcome" };
const tlDate = (iso) => {
  if (!iso) return "—";
  const s = String(iso).slice(0, 10);
  const [y, m, d] = s.split("-").map(Number);
  if (!y) return s;
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
};

const ROLE_LABEL = {
  primary: "Primary agreement", amendment: "Amendment",
  order_form: "Order form", exhibit: "Exhibit", sla: "SLA",
};

const SCANNED_MESSAGE =
  "This looks like a scanned or image-based PDF. ClauseClock cannot read it yet. Upload a text-based version.";

export default function ContractDetail() {
  const { contractId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [findings, setFindings] = useState([]);
  const [status, setStatus] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState("");
  const [warnings, setWarnings] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [supersededCount, setSupersededCount] = useState(0);

  const load = useCallback(() => {
    api.get(`/contracts/${contractId}`)
      .then((r) => setData(r.data))
      .catch(() => setNotFound(true));
    api.get(`/contracts/${contractId}/findings`)
      .then((r) => { setFindings((r.data.findings || []).filter((f) => f.type === "renewal_notice" || f.type === "price_increase" || f.type === "renewal_with_escalation" || f.type === "termination_right")); setStatus(r.data.status); setSupersededCount(r.data.superseded_count || 0); })
      .catch(() => {});
    api.get(`/contracts/${contractId}/timeline`)
      .then((r) => setTimeline(r.data.events || []))
      .catch(() => {});
  }, [contractId]);

  useEffect(() => { load(); }, [load]);

  const analyze = async () => {
    setAnalyzing(true);
    setAnalyzeError("");
    try {
      const { data: res } = await api.post(`/contracts/${contractId}/analyze`);
      setFindings((res.findings || []).filter((f) => f.type === "renewal_notice" || f.type === "price_increase" || f.type === "renewal_with_escalation" || f.type === "termination_right"));
      setWarnings(res.warnings || []);
      setStatus("analysed");
      load();
    } catch (err) {
      setAnalyzeError(err.response?.data?.detail || "Analysis failed. Try again.");
    } finally {
      setAnalyzing(false);
    }
  };

  const del = async () => {
    await api.delete(`/contracts/${contractId}`);
    navigate("/app/contracts");
  };

  if (notFound)
    return (
      <div data-testid={CONTRACT_DETAIL.root}>
        <p className="cc-plain-english">Contract not found.</p>
      </div>
    );

  if (!data) return <p className="cc-days-remaining">Loading…</p>;

  const { contract, documents } = data;

  return (
    <div data-testid={CONTRACT_DETAIL.root} className="max-w-3xl">
      <button onClick={() => navigate("/app/contracts")}
        className="cc-eyebrow text-ink-soft hover:text-ink flex items-center gap-1.5 mb-6">
        <ArrowLeft className="h-4 w-4" /> Contracts
      </button>

      <div className="flex items-start justify-between gap-4">
        <div>
          <Eyebrow>Contract</Eyebrow>
          <h1 className="cc-finding-title text-2xl mt-2">{contract.name}</h1>
          <p className="cc-days-remaining mt-1">
            {contract.counterparty || "No counterparty"} · {documents.length} document
            {documents.length === 1 ? "" : "s"}
          </p>
        </div>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" data-testid="contract-delete"
              className="border-rule text-stamp hover:bg-card rounded-full h-10 px-4 gap-1.5">
              <Trash2 className="h-4 w-4" /> Delete
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this contract?</AlertDialogTitle>
              <AlertDialogDescription>
                This permanently removes the stored original file(s), extracted text and
                all records for &ldquo;{contract.name}&rdquo;. This cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel data-testid="contract-delete-cancel">Cancel</AlertDialogCancel>
              <AlertDialogAction data-testid="contract-delete-confirm" onClick={del}
                className="bg-stamp text-paper hover:bg-stamp/90">
                Delete permanently
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* Annual value + provenance */}
      <div className="mt-6 rounded-lg border border-rule bg-card p-6">
        <Eyebrow>Annual value</Eyebrow>
        {contract.annual_value != null ? (
          <>
            <p className="cc-money text-2xl mt-2" data-testid="contract-annual-value">
              {money(contract.annual_value, contract.currency)}
            </p>
            <p className="cc-days-remaining mt-1">
              Source: {contract.value_source === "user_entered" ? "entered by you" : contract.value_source}
            </p>
          </>
        ) : (
          <p className="cc-days-remaining mt-2">Not provided.</p>
        )}
      </div>

      {/* Renewal findings (Stage 2) */}
      <div className="mt-8">
        <div className="flex items-center justify-between">
          <Eyebrow>What matters</Eyebrow>
          {data.documents.some((d) => d.extraction_method !== "failed_no_text") && (
            <Button onClick={analyze} disabled={analyzing} data-testid="analyze-button"
              className="bg-seal text-paper hover:bg-seal/90 rounded-full h-9 px-4 gap-1.5">
              <ScanSearch className="h-4 w-4" strokeWidth={2} />
              {analyzing ? "Reading clauses…" : findings.length ? "Re-analyze" : "Find deadlines & increases"}
            </Button>
          )}
        </div>
        <div className="cc-seal-rule mt-4 mb-5" />

        {supersededCount > 0 && (
          <div className="mb-5 rounded-lg border border-pending/40 bg-card px-5 py-4 flex items-start gap-3" data-testid="superseded-notice">
            <AlertTriangle className="h-4 w-4 text-pending mt-0.5 shrink-0" strokeWidth={2} />
            <p className="cc-days-remaining text-ink">
              A newly added document changed {supersededCount} previously reviewed finding{supersededCount === 1 ? "" : "s"}.
              The updated finding{supersededCount === 1 ? " is" : "s are"} shown below as unconfirmed — review {supersededCount === 1 ? "it" : "them"} against the source clause. Your earlier reviewed version is preserved.
            </p>
          </div>
        )}

        {analyzeError && <p className="cc-days-remaining text-stamp mb-4" data-testid="analyze-error">{analyzeError}</p>}

        {data.documents.length === 1 && findings.length > 0 && (
          <div className="mb-5 rounded-md border border-rule bg-card px-4 py-3" data-testid="single-doc-warning">
            <p className="cc-days-remaining text-ink-soft">
              Based on a single document. Adding any amendment, order form, exhibit, or SLA may change this analysis — upload it to re-analyze the full set.
            </p>
          </div>
        )}

        {findings.length === 0 && !analyzing && (
          <div className="rounded-lg border border-rule bg-card px-6 py-8">
            {status === "analysed" || warnings.length > 0 ? (
              <>
                <p className="cc-finding-title text-ink text-[16px]">Nothing actionable found</p>
                <p className="cc-plain-english text-ink-soft mt-2">
                  {warnings.length > 0
                    ? warnings[0]
                    : "No renewal or price-increase terms were found in this document."}
                </p>
                <p className="cc-days-remaining mt-3 max-w-xl">
                  ClauseClock currently looks for renewal deadlines and price-increase terms or
                  objection windows. If you expected one, review the extracted text below to make
                  sure the relevant page was read correctly.
                </p>
              </>
            ) : (
              <p className="cc-plain-english text-ink-soft">
                Run analysis to find renewal deadlines, price increases, and the clauses that prove them.
              </p>
            )}
          </div>
        )}

        {analyzing && (
          <div className="rounded-lg border border-rule bg-card px-6 py-8" data-testid="analysis-progress">
            <ol className="space-y-3">
              {["Reading the document",
                "Locating renewal and pricing language",
                "Verifying quotes against the original"].map((stage) => (
                <li key={stage} className="flex items-center gap-3">
                  <Loader2 className="h-4 w-4 text-seal animate-spin" strokeWidth={2} />
                  <span className="cc-plain-english text-ink">{stage}</span>
                </li>
              ))}
            </ol>
            <p className="cc-days-remaining mt-4 max-w-xl">
              We don’t estimate missing terms. If something can’t be verified, ClauseClock will
              flag it for review.
            </p>
          </div>
        )}

        <div className="space-y-6">
          {findings.map((f) => (
            <FindingCard key={f.id} finding={f}
              onChanged={(u) => setFindings((fs) => fs.map((x) => (x.id === u.id ? u : x)))} />
          ))}
        </div>
      </div>

      {/* Outcome timeline (Stage 6D) */}
      {timeline.length > 0 && (
        <div className="mt-8" data-testid={TIMELINE.root}>
          <Eyebrow>Timeline</Eyebrow>
          <div className="cc-seal-rule mt-4 mb-5" />
          <ol className="relative border-l border-rule ml-2 space-y-5">
            {timeline.map((ev, i) => (
              <li key={i} className="ml-5" data-testid={`timeline-${ev.kind}-${i}`}>
                <span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full bg-seal" />
                <p className="cc-section-ref text-ink-soft">{tlDate(ev.date)} · {KIND_LABEL[ev.kind]}</p>
                <p className="cc-plain-english text-ink mt-0.5">{ev.title}</p>
                {ev.detail && <p className="cc-days-remaining mt-0.5">{ev.detail}</p>}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Documents + extracted text */}
      <div className="mt-8">
        <Eyebrow>Documents &amp; extracted text</Eyebrow>
        <div className="mt-4 space-y-6">
          {documents.map((doc) => (
            <div key={doc.id} data-testid={`document-${doc.id}`}
              className="rounded-lg border border-rule bg-card overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-rule">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-ink-soft" strokeWidth={1.75} />
                  <div>
                    <p className="cc-finding-title text-[16px]">{doc.filename}</p>
                    <p className="cc-section-ref mt-0.5">
                      {ROLE_LABEL[doc.doc_role] || doc.doc_role}
                      {doc.page_count != null && ` · ${doc.page_count} page${doc.page_count === 1 ? "" : "s"}`}
                      {` · ${doc.file_type.toUpperCase()}`}
                      {` · ${(doc.size_bytes / 1024).toFixed(0)} KB`}
                    </p>
                  </div>
                </div>
                <span className="cc-section-ref">{doc.extraction_method}</span>
              </div>

              {doc.extraction_method === "failed_no_text" ? (
                <div className="px-5 py-6 flex items-start gap-3 bg-card"
                  data-testid={`document-scanned-${doc.id}`}>
                  <AlertTriangle className="h-5 w-5 text-pending mt-0.5" strokeWidth={2} />
                  <p className="cc-plain-english text-ink">{SCANNED_MESSAGE}</p>
                </div>
              ) : (
                <pre
                  data-testid={`document-rawtext-${doc.id}`}
                  className="cc-clause bg-document px-5 py-5 max-h-[420px] overflow-auto whitespace-pre-wrap m-0">
{doc.raw_text}
                </pre>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
