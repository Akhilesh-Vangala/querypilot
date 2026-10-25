/** Reviewed entry points. Selecting a template never executes an investigation. */
export const STARTERS = [
  {
    label: "Explain a change",
    question: "What explains the change in claims paid between Q1 and Q2 2026?",
    detail: "Periods · weighted contributions · factor accounting",
    icon: "compare",
  },
  {
    label: "Explore spend",
    question: "Claims paid by specialty",
    detail: "Executed SQL · source-derived totals",
    icon: "analyses",
  },
  {
    label: "Inspect referrals",
    question: "Declined referral rate by specialty",
    detail: "Reviewed denominator · metric definition",
    icon: "query",
  },
];
export const investigationLink = (question: string, reference?: string) =>
  "/new?" +
  new URLSearchParams({
    question: question.slice(0, 4000),
    ...(reference ? { reference } : {}),
  }).toString();
