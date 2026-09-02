import { CalendarDays } from "lucide-react";
import { Button } from "@/components/ui/button";
import { localDaysRemaining } from "@/lib/dates";

const CALENDAR_LABEL = {
  renewal_notice: "Contract non-renewal deadline",
  renewal_with_escalation: "Renewal and price increase deadline",
  termination_right: "Contract termination notice deadline",
  price_increase: "Price increase objection deadline",
  service_credit: "Service credit claim deadline",
  invoice_dispute: "Invoice dispute deadline",
  notice_requirement: "Contract notice deadline",
  fee_or_penalty: "Fee or penalty deadline",
  rebate_or_refund: "Rebate or refund deadline",
  warranty_claim: "Warranty claim deadline",
};

function nextDateIso(iso) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10);
}

function icsDate(iso) {
  return iso.replaceAll("-", "");
}

function icsText(value) {
  return String(value || "")
    .replaceAll("\\", "\\\\")
    .replaceAll("\n", "\\n")
    .replaceAll(",", "\\,")
    .replaceAll(";", "\\;");
}

function downloadCalendar(finding, deadline) {
  const label = CALENDAR_LABEL[finding.type] || "Contract deadline";
  const calendar = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//ClauseClock//Deadline Calendar//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VEVENT",
    `UID:${icsText(`clauseclock-${finding.id || deadline}@clauseclock`)}`,
    `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z")}`,
    `DTSTART;VALUE=DATE:${icsDate(deadline)}`,
    `DTEND;VALUE=DATE:${icsDate(nextDateIso(deadline))}`,
    `SUMMARY:${icsText(`ClauseClock · ${label}`)}`,
    `DESCRIPTION:${icsText(`ClauseClock finding: ${label}. Deadline: ${deadline}. Verify the cited contract language before acting.`)}`,
    "END:VEVENT",
    "END:VCALENDAR",
    "",
  ].join("\r\n");

  const blob = new Blob([calendar], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `clauseclock-deadline-${deadline}.ics`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function AddToCalendarButton({ finding, mobile = false }) {
  const deadline = finding?.extracted?.effective_action_deadline;
  const daysRemaining = deadline ? localDaysRemaining(deadline) : null;
  const reviewed = finding?.state === "confirmed" || finding?.state === "corrected";
  const eligible = reviewed
    && finding?.validation_status === "validated"
    && finding?.action_required
    && deadline
    && daysRemaining != null
    && daysRemaining >= 0;

  if (!eligible) return null;

  return (
    <Button
      type="button"
      size="sm"
      variant="outline"
      data-testid={mobile ? `finding-add-calendar-mobile-${finding.id}` : `finding-add-calendar-${finding.id}`}
      onClick={() => downloadCalendar(finding, deadline)}
      className={mobile
        ? "rounded-full h-8 px-3 gap-1.5 border-rule text-ink hover:text-ink hover:border-ink-soft hover:bg-card font-semibold font-sans text-xs"
        : "rounded-full h-9 px-4 gap-1.5 border-rule text-ink hover:text-ink hover:border-ink-soft hover:bg-card font-semibold"}
    >
      <CalendarDays className={mobile ? "h-3.5 w-3.5" : "h-4 w-4"} strokeWidth={2} />
      Add to calendar
    </Button>
  );
}
