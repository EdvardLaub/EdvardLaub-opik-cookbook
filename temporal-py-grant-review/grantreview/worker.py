"""The worker: a separate OS process that runs the workflow and its activities."""

import asyncio
import os
import signal

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

from grantreview.activities import check_eligibility, draft_letter, score_application
from grantreview.models import TASK_QUEUE
from grantreview.tracing import flush, setup_tracing
from grantreview.workflows import GrantReviewWorkflow


async def run_worker(address: str) -> None:
    # The worker process exports its own spans; the interceptor must be on BOTH the client
    # it connects with and the Worker, or workflow and activity spans lose their parent.
    interceptor = setup_tracing("grant-review-worker")
    client = await Client.connect(address, interceptors=[interceptor])
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GrantReviewWorkflow],
        activities=[check_eligibility, score_application, draft_letter],
        interceptors=[interceptor],
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    async with worker:
        await stop.wait()
    # A killed process would drop the spans still waiting in the batch exporter.
    flush()


def main() -> None:
    load_dotenv()
    load_dotenv("../.env")
    try:
        asyncio.run(run_worker(os.getenv("TEMPORAL_ADDRESS", "localhost:7233")))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
