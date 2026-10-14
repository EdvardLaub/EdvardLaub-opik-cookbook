// Standalone: create (or confirm) the online evaluation rule, then exit.
import { config } from "dotenv";
import { PROJECT_NAME } from "../src/lib/config";
import { ensureProject, ensureRule, RULE_NAME } from "../src/lib/online-rule";

config({ path: new URL("../../.env", import.meta.url).pathname, quiet: true });
const projectId = await ensureProject(PROJECT_NAME);
const rule = await ensureRule(projectId);
console.log(`${rule.created ? "Created" : "Found"} rule "${RULE_NAME}" (${rule.id}) on project ${PROJECT_NAME}.`);
