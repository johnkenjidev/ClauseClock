// Upload shell — PART 2 Upload screen structure: drag-and-drop area, document
// role selector, optional annual value. NO upload/analysis logic (later stage).
import { UploadCloud } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Eyebrow, StageNote } from "@/components/cc/Primitives";
import { UPLOAD } from "@/constants/testIds";

const DOC_ROLES = [
  ["primary", "Primary agreement"],
  ["amendment", "Amendment"],
  ["order_form", "Order form"],
  ["exhibit", "Exhibit"],
  ["sla", "SLA"],
];

export default function Upload() {
  return (
    <div data-testid={UPLOAD.root} className="max-w-xl">
      <Eyebrow>Add a contract</Eyebrow>
      <div className="cc-seal-rule mt-4 mb-8" />

      <div className="rounded-lg border-2 border-dashed border-rule bg-card px-8 py-14 flex flex-col items-center text-center">
        <UploadCloud className="h-8 w-8 text-ink-soft" strokeWidth={1.75} />
        <p className="cc-plain-english mt-4">
          Drag and drop a PDF or DOCX, or browse.
        </p>
        <p className="cc-days-remaining mt-1">Text-based documents only.</p>
      </div>

      <div className="mt-8 space-y-6">
        <div className="space-y-2">
          <Label className="cc-eyebrow" htmlFor="doc-role">
            Document role
          </Label>
          <Select disabled>
            <SelectTrigger id="doc-role" className="bg-card border-rule">
              <SelectValue placeholder="Primary agreement" />
            </SelectTrigger>
            <SelectContent>
              {DOC_ROLES.map(([v, label]) => (
                <SelectItem key={v} value={v}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="cc-eyebrow" htmlFor="annual-value">
            Annual value (optional)
          </Label>
          <Input
            id="annual-value"
            disabled
            placeholder="e.g. 24000"
            className="bg-card border-rule cc-money"
          />
        </div>
      </div>

      <StageNote>
        Scaffold only. Upload handling, scanned-document detection, extraction
        and analysis are built in later stages. Controls are inert for now.
      </StageNote>
    </div>
  );
}
