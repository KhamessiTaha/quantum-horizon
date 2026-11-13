import { useEffect, useState } from "react";

type Copied = "link" | "embed" | null;

export default function ShareButtons() {
  const [copied, setCopied] = useState<Copied>(null);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(null), 1800);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function copy(kind: Exclude<Copied, null>) {
    const url = new URL(window.location.href);
    url.searchParams.delete("embed");
    const link = url.toString();
    url.searchParams.set("embed", "1");
    const text =
      kind === "link"
        ? link
        : `<iframe src="${url.toString()}" width="760" height="640" style="border:0" title="Quantum Horizon view" loading="lazy"></iframe>`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
    } catch {
      setCopied(null);
    }
  }

  return (
    <div style={{ display: "flex", gap: 8 }}>
      <button type="button" className="btn" onClick={() => copy("link")}>
        {copied === "link" ? "Link copied" : "Copy link"}
      </button>
      <button type="button" className="btn" onClick={() => copy("embed")}>
        {copied === "embed" ? "Embed code copied" : "Embed"}
      </button>
      <span className="visually-hidden" aria-live="polite">
        {copied ? "Copied to clipboard" : ""}
      </span>
    </div>
  );
}
