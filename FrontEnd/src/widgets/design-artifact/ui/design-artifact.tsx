export function DesignArtifactPanel({ markdown }: { markdown: string }) {
  return (
    <aside className="artifact-panel" aria-label="Design brief">
      <article className="artifact-document">
        <MarkdownPreview markdown={markdown} />
      </article>
    </aside>
  );
}

function MarkdownPreview({ markdown }: { markdown: string }) {
  return markdown.split("\n").map((line, index) => {
    if (line.startsWith("# ")) return <h1 key={index}>{line.slice(2)}</h1>;
    if (line.startsWith("## ")) return <h2 key={index}>{line.slice(3)}</h2>;
    if (line.startsWith("### ")) return <h3 key={index}>{line.slice(4)}</h3>;
    if (line.startsWith("- ")) return <li key={index}>{line.slice(2)}</li>;
    if (!line.trim()) return <div className="markdown-space" key={index} />;
    return <p key={index}>{line}</p>;
  });
}
