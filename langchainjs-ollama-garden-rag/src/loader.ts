import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

export interface Chunk {
  /** Stable id such as "composting#what-goes-in-the-bins". */
  id: string;
  /** File the chunk came from, without extension. */
  source: string;
  heading: string;
  /** Text that gets embedded and, later, pasted into the prompt. */
  text: string;
}

const slug = (s: string): string => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

/** Split one markdown file into one chunk per "## " section, each prefixed with the file title. */
export function chunkMarkdown(source: string, markdown: string): Chunk[] {
  const [titleBlock = "", ...sections] = markdown.split(/\n## /);
  const title = titleBlock.replace(/^#\s*/, "").trim();
  return sections.map((section) => {
    const [heading = "", ...body] = section.split("\n");
    return {
      id: `${source}#${slug(heading)}`,
      source,
      heading: heading.trim(),
      text: `${title}\n## ${heading.trim()}\n${body.join("\n").trim()}`,
    };
  });
}

/** Read every .md file in a folder and chunk it. Files are sorted so chunk order is stable. */
export async function loadChunks(dir: string): Promise<Chunk[]> {
  const files = (await readdir(dir)).filter((f) => f.endsWith(".md")).sort();
  const perFile = await Promise.all(
    files.map(async (f) => chunkMarkdown(path.basename(f, ".md"), await readFile(path.join(dir, f), "utf8"))),
  );
  return perFile.flat();
}
