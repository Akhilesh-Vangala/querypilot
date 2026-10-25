/** Navigation labels remain visible; icons are decorative. */
export default function StudioIcon({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  const paths: Record<string, string> = {
    overview: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    analyses: "M4 20V10 M10 20V4 M16 20v-8 M22 20H2",
    projects: "M3 6h7l2 3h9v11H3z M3 6V4h7l2 2",
    guide: "M12 6C9 3 5 3 2 4v15c4-1 7-1 10 2 3-3 6-3 10-2V4c-3-1-7-1-10 2v15",
    settings:
      "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2",
    upload: "M12 16V3 M7 8l5-5 5 5 M3 15v6h18v-6",
    query: "M9 5 2 12l7 7 M15 5l7 7-7 7",
    check: "M4 12l5 5L20 6",
    arrow: "M4 12h16 M14 6l6 6-6 6",
    search: "M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6",
    clock: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20 M12 6v6l4 2",
    compare: "M4 6h16 M16 2l4 4-4 4 M20 18H4 M8 14l-4 4 4 4",
    data: "M3 3h18v18H3z M3 9h18 M3 15h18 M9 3v18",
  };
  return (
    <svg
      className={`studio-icon ${className}`}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.query} />
    </svg>
  );
}
