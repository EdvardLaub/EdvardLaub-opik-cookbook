/** One release of the fictional open-source project "Tidepool" (a log-tailing CLI). */
export interface Release {
  /** Stable id, also used to avoid inserting the same suite item twice. */
  id: string;
  version: string;
  /** Raw `git log --oneline` lines: short hash, then the commit message. */
  commits: string[];
}

export const RELEASES: Release[] = [
  {
    id: "tidepool-2.0.0",
    version: "2.0.0",
    commits: [
      "d41e8aa feat!: drop Node 16, minimum runtime is now Node 18",
      "0c5a4d8 feat!: rename config key `sinks` to `outputs` (BREAKING CHANGE: old key is silently ignored)",
      "b81d7e4 feat(cli): add --since flag to filter lines by relative time, e.g. --since 15m",
      "c0de5f9 refactor(core): migrate StreamMux to ringbuf v3 [TIDE-871]",
      "f2a90b6 chore(ci): pin actions/checkout, quarantine flaky matrix job",
    ],
  },
  {
    id: "tidepool-1.9.2",
    version: "1.9.2",
    commits: [
      "a3f9c21 fix(parser): skip empty NDJSON lines instead of crashing (closes #412)",
      "e77b2c3 fix(tls): bump tlsx to 4.2.1 to patch CVE-2026-1182",
      "7be10d4 test(parser): add fuzz cases for LineSplitter",
      "5c8e3a9 docs: fix typo in CONTRIBUTING",
    ],
  },
  {
    id: "tidepool-1.9.0",
    version: "1.9.0",
    commits: [
      "91bd3e0 perf(index): lazy-load PluginRegistry, cold start 340ms -> 120ms",
      "2a6f7c8 feat(cli): colorize log levels, disable with --no-color or NO_COLOR=1",
      "38d0b15 refactor(sink): extract BackpressureGate from SinkWriter [TIDE-802]",
      "ce41f90 fix(tail): follow log rotation when the file is renamed (fixes #377)",
    ],
  },
  {
    id: "tidepool-2.1.0",
    version: "2.1.0",
    commits: [
      "6f1d2b7 feat(output): add `outputs[].format = \"json\"` for machine-readable lines",
      "b90c4e2 fix!: `--since` now interprets bare numbers as seconds, not minutes (BREAKING)",
      "14ad8f3 chore(deps): bump vitest to 3.1, eslint to 9.4",
      "d7e5a60 fix(cli): --help no longer prints the internal debug flags",
    ],
  },
  {
    id: "tidepool-2.1.1",
    version: "2.1.1",
    commits: [
      "8c3b9d1 fix(output): flush buffered lines on SIGTERM so none are lost at shutdown",
      "f0a72e6 refactor(core): inline MuxScheduler, delete dead code [TIDE-930]",
      "3d19c8b ci: cache npm between jobs",
    ],
  },
];
