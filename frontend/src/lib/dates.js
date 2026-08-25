// Shared date-only, local-calendar countdown helper. A date-only deadline
// (YYYY-MM-DD) is compared against the browser's local calendar date, never
// UTC/server time, so "today" always matches what the user sees on their
// clock. Used by FindingCard and Action Center — do not reimplement.
export const localDaysRemaining = (deadlineIso) => {
  if (!deadlineIso) return null;
  const [y, m, d] = deadlineIso.split("-").map(Number);
  const deadlineDate = new Date(y, m - 1, d);
  deadlineDate.setHours(0, 0, 0, 0);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffTime = deadlineDate - today;
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
};
