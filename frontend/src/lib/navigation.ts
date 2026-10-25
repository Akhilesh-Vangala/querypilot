/** Resume only a known internal investigation route after authentication. */
export function investigationReturn(value: unknown): string {
  if (
    typeof value !== "string" ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\")
  )
    return "/demo";
  try {
    const target = new URL(value, window.location.origin);
    if (
      target.origin !== window.location.origin ||
      !/^\/(?:demo|new|compare|history|metrics|schema|settings|eval|runs\/[a-zA-Z0-9_-]+)$/.test(
        target.pathname,
      )
    )
      return "/demo";
    return target.pathname + target.search;
  } catch {
    return "/demo";
  }
}
