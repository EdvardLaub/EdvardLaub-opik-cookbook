"""Self-contained demo: dev server, a separately spawned worker, and the client."""

import asyncio
import os
import subprocess
import sys

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

from grantreview.data import APPLICATIONS
from grantreview.models import TASK_QUEUE, Application, Review
from grantreview.workflows import GrantReviewWorkflow

# Ports 4240-4249 are reserved for this example; never the default 7233.
SERVER_PORT = int(os.getenv("TEMPORAL_PORT", "4240"))
UI_PORT = int(os.getenv("TEMPORAL_UI_PORT", "4241"))


async def review(client: Client, app: Application) -> Review:
    return await client.execute_workflow(
        GrantReviewWorkflow.run, app, id=f"grant-review-{app.id}", task_queue=TASK_QUEUE
    )


async def run_demo() -> None:
    # start_local downloads and launches the Temporal dev server: no Docker, no account.
    env = await WorkflowEnvironment.start_local(port=SERVER_PORT, ui=True, ui_port=UI_PORT)
    address = f"localhost:{SERVER_PORT}"
    # The worker is a real second process, as it would be in production.
    worker = subprocess.Popen(
        [sys.executable, "-m", "grantreview.worker"],
        env={**os.environ, "TEMPORAL_ADDRESS": address},
    )
    try:
        client = await Client.connect(address)
        reviews = await asyncio.gather(*(review(client, a) for a in APPLICATIONS))
        for app, r in zip(APPLICATIONS, reviews):
            print(f"\n=== {app.id} {app.applicant}: {r.decision.upper()}")
            if r.score:
                print(f"score {r.score.total}/15 - {r.score.rationale}")
            for reason in r.eligibility_reasons:
                print(f"ineligible: {reason}")
            print(r.letter)
    finally:
        worker.terminate()
        worker.wait(timeout=15)
        await env.shutdown()


def main() -> None:
    load_dotenv()
    load_dotenv("../.env")
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
