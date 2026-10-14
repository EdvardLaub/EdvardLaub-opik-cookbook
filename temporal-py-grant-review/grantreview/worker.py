"""The worker: a separate OS process that runs the workflow and its activities."""

import asyncio
import os

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

from grantreview.activities import check_eligibility, draft_letter, score_application
from grantreview.models import TASK_QUEUE
from grantreview.workflows import GrantReviewWorkflow


async def run_worker(address: str) -> None:
    client = await Client.connect(address)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GrantReviewWorkflow],
        activities=[check_eligibility, score_application, draft_letter],
    )
    await worker.run()


def main() -> None:
    load_dotenv()
    load_dotenv("../.env")
    try:
        asyncio.run(run_worker(os.getenv("TEMPORAL_ADDRESS", "localhost:7233")))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
