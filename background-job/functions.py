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


@client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
)
async def make_report(ctx: inngest.Context) -> dict:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

    def build_report() -> dict:
        result = {"summary": f"Report about {topic}", "word_count": 42}
        report = reports.get(report_id)
        if report is not None:
            report["status"] = "done"
            report["result"] = result
        return result

    return await ctx.step.run("build-report", build_report)
