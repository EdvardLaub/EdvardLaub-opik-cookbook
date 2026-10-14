"""Let Opik's Agent Optimizer improve a deliberately weak wildlife-report router."""

import os
import pathlib

PROJECT_NAME = "optimizer-wildlife-report-classifier"
# Every trace, trial and prompt-library entry is filed under this project.
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).parents[1] / ".env")  # repo-root keys
dotenv.load_dotenv()  # or a local .env
# A local proxy base URL would silently reroute the calls; use the public API.
os.environ.pop("OPENAI_BASE_URL", None)
os.environ.pop("OPENAI_API_BASE", None)

import opik
from opik_optimizer import ChatPrompt, MetaPromptOptimizer

from classify import classify_report
from scoring import label_accuracy
from sightings import REPORTS

MODEL = "openai/gpt-4o-mini"  # LiteLLM naming: the classifier being tuned
REASONER = "openai/gpt-4.1-mini"  # writes the candidate prompts; a bit sharper at spotting format failures
DATASET_NAME = "wildlife-reports-labelled"
LIBRARY_PROMPT_NAME = "wildlife-report-router"
MAX_TRIALS = 6

WEAK_SYSTEM = """\
You help the Marshline Nature Watch app. People send in short notes about
what they saw outdoors. The groups are: birds, mammals, reptiles_amphibians,
insects, marine_life, not_a_sighting. Work out which group the note belongs to."""

NEW_REPORT = "Little egret fishing in the shallows by the sluice gate, white with black legs and yellow feet."

opik_client = opik.Opik()

# The dataset is the ground truth every trial is scored against; Opik dedupes
# identical rows, so re-runs reuse it. It appears under Datasets.
dataset = opik_client.get_or_create_dataset(
    name=DATASET_NAME, description="36 fictional wildlife reports, 6 routing groups"
)
dataset.insert([{"report": text, "label": label} for text, label in REPORTS])

prompt = ChatPrompt(name="wildlife-router", system=WEAK_SYSTEM, user="{report}", model=MODEL)

# Version 1 in the prompt library is the weak baseline, so the library ends up
# showing v1 (weak) next to v2 (optimized) with a change description each.
opik_client.create_chat_prompt(
    name=LIBRARY_PROMPT_NAME,
    messages=[
        {"role": "system", "content": WEAK_SYSTEM},
        {"role": "user", "content": "{{report}}"},
    ],
    change_description="Weak hand-written baseline",
    project_name=PROJECT_NAME,
)

# The optimizer creates an Optimization run (the score-vs-trial curve), one
# experiment per trial, and traces for every LLM call, all in this project.
optimizer = MetaPromptOptimizer(model=REASONER, prompts_per_round=4, seed=7, verbose=1,
    skip_perfect_score=False)  # keep trying after a ~perfect round so the whole curve is logged
result = optimizer.optimize_prompt(
    prompt=prompt,
    dataset=dataset,
    metric=label_accuracy,
    n_samples=len(REPORTS),
    max_trials=MAX_TRIALS,
    project_name=PROJECT_NAME,
)

initial = result.initial_score or 0.0
best = result.score
print("\n" + "=" * 64)
print(f"baseline accuracy : {initial:.3f}")
print(f"best accuracy     : {best:.3f}  ({best - initial:+.3f})")
print(f"trials completed  : {result.details.get('trials_completed')}  (cap {MAX_TRIALS})")
print(f"llm cost (optim.) : {result.llm_cost_total}")

# get_run_link() opens in whichever project the UI last showed, so the run can
# look empty. Build a project-pinned link from the optimization record instead.
try:
    info = opik_client.rest_client.optimizations.get_optimization_by_id(result.optimization_id)
    ui = opik_client.config.url_override.rstrip("/").removesuffix("/api")
    print(f"run link          : {ui}/{opik_client.config.workspace}/projects/{info.project_id}"
          f"/optimizations/{result.optimization_id}")
except Exception as exc:  # the lookup is a convenience; never lose the run over it
    print(f"run link          : {result.get_run_link()}  (project-pinned lookup failed: {exc.__class__.__name__})")
print("=" * 64)

if best > initial:
    messages = result.prompt.get_messages()
    for m in messages:  # optimizer uses {report}; the library uses mustache {{report}}
        m["content"] = m["content"].replace("{report}", "{{report}}")
    # Same prompt name -> a new immutable version 2 with the score in its changelog.
    opik_client.create_chat_prompt(
        name=LIBRARY_PROMPT_NAME,
        messages=messages,
        change_description=f"MetaPromptOptimizer winner: accuracy {initial:.3f} -> {best:.3f} on {DATASET_NAME}",
        project_name=PROJECT_NAME,
    )
    print(f"Saved winner as '{LIBRARY_PROMPT_NAME}' v2.\n\nWinning system prompt:\n{messages[0]['content']}\n")

    # Prove the saved prompt works outside the optimizer: pull it back from the
    # library and route a new report. This produces one `classify_report` trace.
    saved = opik_client.get_chat_prompt(name=LIBRARY_PROMPT_NAME, project_name=PROJECT_NAME)
    print("Fresh report ->", classify_report(saved.template, NEW_REPORT)["label"])
else:
    print("No improvement; the library keeps only v1.")

opik.flush_tracker()  # make sure the last traces are sent before exit
