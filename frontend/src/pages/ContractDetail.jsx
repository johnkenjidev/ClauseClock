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

const longDate = (iso) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
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
  const [expandedDocs, setExpandedDocs] = useState({});

  const toggleDoc = (id) => {
    setExpandedDocs((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const load = useCallback(() => {
    api.get(`/contracts/${contractId}`)
      .then((r) => setData(r.data))
      .catch(() => setNotFound(true));
    api.get(`/contracts/${contractId}/findings`)
      .then((r) => { setFindings((r.data.findings || []).filter((f) => f.type === "renewal_notice" || f.type === "price_increase" || f.type === "renewal_with_escalation" || f.type === "termination_right" || f.type === "service_credit" || f.type === "invoice_dispute" || f.type === "notice_requirement" || f.type === "fee_or_penalty" || f.type === "rebate_or_refund" || f.type === "warranty_claim")); setStatus(r.data.status); setSupersededCount(r.data.superseded_count || 0); })
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
      setFindings((res.findings || []).filter((f) => f.type === "renewal_notice" || f.type === "price_increase" || f.type === "renewal_with_escalation" || f.type === "termination_right" || f.type === "service_credit" || f.type === "invoice_dispute" || f.type === "notice_requirement" || f.type === "fee_or_penalty" || f.type === "rebate_or_refund" || f.type === "warranty_claim"));
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
    <div data-testid={CONTRACT_DETAIL.root}>
      <style dangerouslySetInnerHTML={{ __html: `
        @media (max-width: 768px) {
          .hidden-on-mobile {
            display: none !important;
          }
        }
      ` }} />
      {/* Desktop-only view */}
      <div className="hidden md:block max-w-3xl hidden-on-mobile">
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

      {/* Mobile-only Layout (visible only below md breakpoint) */}
      <div className="md:hidden space-y-6 animate-cc-settle">
        <button onClick={() => navigate("/app/contracts")}
          className="cc-eyebrow text-ink-soft hover:text-ink flex items-center gap-1 mb-4 font-sans font-semibold text-xs bg-transparent border-0 p-0 cursor-pointer">
          ← Contracts
        </button>

        {/* 1. Contract identity/meta */}
        <div className="space-y-2">
          <Eyebrow className="font-sans">Contract</Eyebrow>
          <h1 className="cc-finding-title text-2xl font-bold break-words line-clamp-2 leading-tight text-ink mt-1">
            {contract.name}
          </h1>
          <p className="cc-days-remaining text-xs text-ink-soft leading-normal font-sans">
            {contract.counterparty || "No counterparty"} · {documents.length} doc{documents.length === 1 ? "" : "s"}
            {contract.annual_value != null && <> · <span className="cc-money font-semibold text-ink text-xs">{money(contract.annual_value, contract.currency)}</span></>}
          </p>

          <div className="flex flex-wrap items-center gap-4 pt-2">
            {data.documents.some((d) => d.extraction_method !== "failed_no_text") && (
              <button 
                onClick={analyze} 
                disabled={analyzing} 
                className="text-ink-soft hover:text-ink hover:underline text-xs bg-transparent border-0 p-0 font-sans tracking-wide uppercase font-semibold cursor-pointer"
              >
                {analyzing ? "Reading clauses…" : "Re-analyze"}
              </button>
            )}

            <button 
              onClick={() => {
                if (window.confirm("Permanently delete this contract? This cannot be undone.")) {
                  del();
                }
              }}
              className="text-ink-soft hover:text-ink hover:underline text-xs bg-transparent border-0 p-0 font-sans tracking-wide uppercase font-semibold cursor-pointer"
            >
              Delete Contract
            </button>
          </div>

          {analyzeError && <p className="cc-days-remaining text-stamp text-xs" data-testid="analyze-error">{analyzeError}</p>}

          {data.documents.length === 1 && findings.length > 0 && (
            <p className="text-ink-soft text-xs leading-normal font-sans pt-1">
              Based on a single document. Adding amendments or SLAs may change this analysis.
            </p>
          )}
        </div>

        {/* 2, 3, 4, 5. Urgent finding + primary action, explanation, source language, reminders (all inside FindingCard!) */}
        <div className="space-y-4 pt-4 border-t border-rule">
          <Eyebrow className="font-sans">What matters</Eyebrow>
          {findings.length === 0 && !analyzing && (
            <div className="bg-card border border-rule p-4 rounded text-center">
              <p className="text-xs text-ink-soft font-sans">No actionable findings found.</p>
            </div>
          )}

          {analyzing && (
            <div className="bg-card border border-rule p-5 rounded space-y-3">
              <span className="cc-eyebrow font-sans">Analysis progress</span>
              <p className="text-xs text-ink font-sans leading-normal">Locating and verifying clauses from the document...</p>
            </div>
          )}

          <div className="space-y-4">
            {findings.map((f) => (
              <FindingCard key={f.id} finding={f} readOnly={false}
                onChanged={(u) => setFindings((fs) => fs.map((x) => (x.id === u.id ? u : x)))} />
            ))}
          </div>
        </div>

        {/* 6. Timeline (with neutral ground/UI styling and font-sans) */}
        {timeline.length > 0 && (
          <div className="pt-4 border-t border-rule space-y-3" data-testid={TIMELINE.root}>
            <span className="cc-eyebrow font-sans">Timeline</span>
            <ol className="relative border-l border-rule ml-2 space-y-4 font-sans">
              {timeline.map((ev, i) => (
                <li key={i} className="ml-5 relative" data-testid={`timeline-${ev.kind}-${i}`}>
                  <span className="absolute -left-[25px] mt-1.5 h-2 w-2 rounded-full bg-ink-soft border border-rule bg-paper" />
                  <p className="text-[10px] text-ink-soft font-semibold uppercase tracking-wider">{tlDate(ev.date)} · {KIND_LABEL[ev.kind]}</p>
                  <p className="text-xs text-ink font-medium mt-0.5 leading-relaxed">{ev.title}</p>
                  {ev.detail && <p className="text-[11px] text-ink-soft mt-0.5">{ev.detail}</p>}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* 7. Documents/extracted text (compact, collapsed rawtext) */}
        <div className="pt-4 border-t border-rule space-y-3">
          <span className="cc-eyebrow font-sans">Documents &amp; Extracted Text</span>
          <div className="space-y-4">
            {documents.map((doc) => (
              <div key={doc.id} className="border border-rule bg-card rounded overflow-hidden" data-testid={`document-${doc.id}`}>
                <div className="p-3 flex items-center justify-between gap-3 text-xs border-b border-rule bg-paper/20">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <FileText className="h-4 w-4 text-ink-soft shrink-0" strokeWidth={2} />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-ink truncate text-xs font-sans leading-snug">{doc.filename}</p>
                      <p className="text-[10px] text-ink-soft mt-0.5 font-sans leading-none">
                        {ROLE_LABEL[doc.doc_role] || doc.doc_role}
                        {doc.page_count != null && ` · ${doc.page_count} page${doc.page_count === 1 ? "" : "s"}`}
                        {` · ${(doc.size_bytes / 1024).toFixed(0)} KB`}
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] text-ink-soft font-semibold shrink-0 uppercase tracking-wider font-sans pr-1">{doc.extraction_method}</span>
                </div>

                {doc.extraction_method === "failed_no_text" ? (
                  <div className="p-4 flex items-start gap-2 bg-card">
                    <AlertTriangle className="h-4 w-4 text-pending shrink-0 mt-0.5" />
                    <p className="text-xs text-ink font-sans leading-relaxed">{SCANNED_MESSAGE}</p>
                  </div>
                ) : (
                  <div className="p-3 bg-card space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] text-ink-soft font-semibold uppercase tracking-wider font-sans">Text Content</span>
                      <button 
                        onClick={() => toggleDoc(doc.id)}
                        className="text-ink-soft hover:text-ink hover:underline font-sans font-semibold text-xs bg-transparent border-0 p-0 cursor-pointer"
                      >
                        {expandedDocs[doc.id] ? "Hide extracted text ⌃" : "Show extracted text ⌄"}
                      </button>
                    </div>

                    {expandedDocs[doc.id] && (
                      <pre className="cc-clause bg-document p-3 rounded-sm font-mono text-xs leading-relaxed max-h-[300px] overflow-auto whitespace-pre-wrap text-document-ink border border-document-rule">
                        {doc.raw_text}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
