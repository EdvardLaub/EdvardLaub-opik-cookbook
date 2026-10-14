import { describe, expect, it } from "vitest";
import { buildContext, loadEvents, loadGuide, retrieveEvents, retrieveGuide, tokenize } from "../src/lib/knowledge";

const guide = loadGuide();
const events = loadEvents();

describe("knowledge", () => {
  it("parses every guide section", () => {
    expect(guide.map((s) => s.title)).toContain("Dark adaptation");
    expect(guide.length).toBeGreaterThanOrEqual(7);
  });

  it("strips plurals and stop words when tokenizing", () => {
    expect(tokenize("Which meteors are there?")).toEqual(["meteor"]);
  });

  it("retrieves the loaner section for a telescope question", () => {
    const top = retrieveGuide("Which loaner telescope is better, Pip or Marlow?", guide, 1)[0];
    expect(top?.title).toBe("Loaner telescopes");
  });

  it("retrieves the Jupiter event", () => {
    expect(retrieveEvents("when is Jupiter at opposition", events, 1)[0]?.title).toBe("Jupiter at Opposition");
  });

  it("says so when nothing matches", () => {
    expect(buildContext("xyzzy plugh", guide, events)).toMatch(/No matching/);
  });
});
