"""Structured logs and metrics the way a Lambda emits them, using AWS Lambda Powertools.

- Logger: JSON lines with service name, and (in Lambda) request id / cold start. Never logs
  a phone number or a complaint's text: the customer's words are personal data.
- Metrics: CloudWatch Embedded Metric Format, printed to stdout. In Lambda, CloudWatch turns
  those lines into metrics with no API call and no agent. Locally they are just JSON lines,
  visible in `sam local` output. Set AFTERCARE_EMF=1 to force them on outside Lambda.
"""

import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools.metrics import MetricUnit, single_metric

logger = Logger(service="aftercare", level=os.environ.get("LOG_LEVEL", "INFO"))
_EMF = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("AFTERCARE_EMF"))


def metric(name: str, value: float = 1, unit: MetricUnit = MetricUnit.Count, **dimensions: str) -> None:
    if not _EMF:
        return
    with single_metric(name=name, unit=unit, value=value, namespace="Aftercare") as m:
        for k, v in dimensions.items():
            m.add_dimension(name=k, value=v)


def conversation_outcome(state: dict, brand: str, agent_ms: float | None = None) -> None:
    """One log line and one metric per conversation step, keyed on facts, not text."""
    status = state.get("status")
    meta = state.get("meta") or {}
    esc = meta.get("escalation") or {}
    logger.info("conversation_step", status=status, brand=brand, section=meta.get("section_heading"),
                retrieval=meta.get("retrieval_method"), attempt=meta.get("attempt"),
                reason_code=esc.get("code"), ticket_id=state.get("ticket_id"), agent_ms=agent_ms)
    if status == "escalated":
        metric("Escalated", Brand=brand, Reason=esc.get("code") or "unknown")
    elif status == "resolved":
        metric("ResolvedByAgent", Brand=brand)
    if agent_ms is not None:
        metric("AgentLatency", agent_ms, MetricUnit.Milliseconds, Brand=brand)
