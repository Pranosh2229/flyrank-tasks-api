import datetime

import inngest

from inngest_client import client
from store import reports


@client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("wait-a-bit", datetime.timedelta(seconds=5))
    return "Hello from the background!"


async def _mark_report_failed(ctx: inngest.Context) -> None:
    original_event = ctx.event.data["event"]
    report_id = original_event["data"]["id"]
    report = reports.get(report_id)
    if report is not None:
        report["status"] = "failed"


@client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
    on_failure=_mark_report_failed,
)
async def make_report(ctx: inngest.Context) -> dict:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

    def build_report() -> dict:
        if topic == "fail":
            raise Exception("The report oven is broken!")

        result = {"summary": f"Report about {topic}", "word_count": 42}
        report = reports.get(report_id)
        if report is not None:
            report["status"] = "done"
            report["result"] = result
        return result

    return await ctx.step.run("build-report", build_report)


@client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def heartbeat(ctx: inngest.Context) -> None:
    statuses = [report["status"] for report in reports.values()]
    pending = statuses.count("pending")
    done = statuses.count("done")
    failed = statuses.count("failed")
    ctx.logger.info(f"heartbeat: pending={pending} done={done} failed={failed}")
