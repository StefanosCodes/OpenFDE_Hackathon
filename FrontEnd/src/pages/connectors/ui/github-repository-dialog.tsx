import { Lock, X } from "lucide-react";
import * as React from "react";

import type { GitHubRepository } from "@/entities/connector/api/github-connector";

export function GitHubRepositoryDialog({
  open,
  repositories,
  accountLogin,
  saving,
  onClose,
  onSelect,
}: {
  open: boolean;
  repositories: GitHubRepository[];
  accountLogin: string | null;
  saving: boolean;
  onClose: () => void;
  onSelect: (repository: GitHubRepository) => void;
}) {
  React.useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose, saving]);

  if (!open) return null;

  return (
    <div className="confirm-overlay" onClick={saving ? undefined : onClose}>
      <div
        className="repository-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="github-repository-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="confirm-dialog__header">
          <div>
            <p id="github-repository-dialog-title">Choose a repository</p>
            <span>{accountLogin ? `Connected as ${accountLogin}` : "GitHub connected"}</span>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close repository selection"
            onClick={onClose}
            disabled={saving}
          >
            <X size={16} />
          </button>
        </div>
        <div className="repository-dialog__body">
          {repositories.length === 0 ? (
            <p className="repository-dialog__empty">
              No repositories were shared with this GitHub App installation.
            </p>
          ) : (
            <ul>
              {repositories.map((repository) => (
                <li key={repository.id}>
                  <button type="button" onClick={() => onSelect(repository)} disabled={saving}>
                    <span>{repository.full_name}</span>
                    <small>
                      {repository.private ? <Lock size={12} aria-label="Private" /> : null}
                      {repository.default_branch}
                    </small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
