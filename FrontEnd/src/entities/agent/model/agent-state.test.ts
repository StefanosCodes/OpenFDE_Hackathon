import { describe, expect, it } from "vitest";

import {
  applyGeneratedCanvas,
  createAgentFromPrompt,
  createCanvasDocument,
  createDesignArtifact,
  deleteAgent,
  getAgentDestination,
  getAgentStage,
  markAgentSubmitted,
  toggleConnectorId,
} from "@/entities/agent/model/agent-state";

function idFactory() {
  let value = 0;
  return () => `id-${++value}`;
}

describe("agent lifecycle", () => {
  it("does not create an agent from an empty new-agent chat", () => {
    expect(createAgentFromPrompt("   ", idFactory(), 100)).toBeNull();
  });

  it("keeps selected connectors and skill on the first saved message", () => {
    const agent = createAgentFromPrompt(
      "Build a friendly onboarding agent",
      idFactory(),
      100,
      { enabledConnectorIds: ["github", "slack"], skillId: "onboarding" },
    );

    expect(agent?.enabledConnectorIds).toEqual(["github", "slack"]);
    expect(agent?.skillId).toBe("onboarding");
  });

  it("creates an in-progress agent on the first real message", () => {
    const agent = createAgentFromPrompt(
      "Build a friendly onboarding agent",
      idFactory(),
      100,
    );

    expect(agent).not.toBeNull();
    expect(agent?.name).toBe("Build a friendly onboarding agent");
    expect(agent?.messages).toHaveLength(2);
    expect(agent?.enabledConnectorIds).toEqual([]);
    expect(agent?.skillId).toBeNull();
    expect(agent && getAgentStage(agent)).toBe("In progress");
    expect(agent && getAgentDestination(agent)).toBe("/agents/id-1/design");
  });

  it("routes a generated visual agent back to its canvas", () => {
    const agent = createAgentFromPrompt("Support agent", idFactory(), 100)!;
    const withBrief = {
      ...agent,
      artifact: createDesignArtifact(agent, idFactory(), 200),
    };
    const withCanvas = {
      ...withBrief,
      canvas: createCanvasDocument(idFactory(), 300),
    };

    expect(getAgentStage(withBrief)).toBe("Brief ready");
    expect(getAgentStage(withCanvas)).toBe("Canvas ready");
    expect(getAgentDestination(withCanvas)).toBe("/agents/id-1/canvas");
    expect(withCanvas.canvas.nodes).toHaveLength(4);
    expect(withCanvas.canvas.edges).toHaveLength(3);
  });

  it("marks a canvas agent as submitted until the map is regenerated", () => {
    const agent = createAgentFromPrompt("Support agent", idFactory(), 100)!;
    const withCanvas = applyGeneratedCanvas(agent, idFactory(), 300);
    const submitted = markAgentSubmitted(withCanvas, 400);

    expect(getAgentStage(withCanvas)).toBe("Canvas ready");
    expect(getAgentStage(submitted)).toBe("Submitted");
    expect(submitted.submittedAt).toBe(400);
    expect(getAgentDestination(submitted)).toBe("/agents/id-1/canvas");
    expect(markAgentSubmitted(submitted, 500).submittedAt).toBe(400);

    const regenerated = applyGeneratedCanvas(submitted, idFactory(), 600);
    expect(regenerated.submittedAt).toBeUndefined();
    expect(getAgentStage(regenerated)).toBe("Canvas ready");
  });

  it("removes only the matching agent from the list", () => {
    const nextId = idFactory();
    const first = createAgentFromPrompt("Onboarding", nextId, 100)!;
    const second = createAgentFromPrompt("Support", nextId, 200)!;

    expect(deleteAgent([first, second], first.id)).toEqual([second]);
    expect(deleteAgent([first, second], "missing")).toEqual([first, second]);
  });

  it("toggles a connector on the agent", () => {
    expect(toggleConnectorId(["github"], "slack")).toEqual(["github", "slack"]);
    expect(toggleConnectorId(["github", "slack"], "github")).toEqual(["slack"]);
  });
});
