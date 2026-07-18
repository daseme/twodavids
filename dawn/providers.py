"""Inference providers behind one narrow interface.

The sim never talks to a model vendor directly; it hands a provider a list of
request dicts and gets back {custom_id: text}. Phase 2 uses the Anthropic
Message Batches API (50% price, results unordered — keyed by custom_id, never
position). MockProvider keeps tests and dry-runs deterministic and offline.
A local-inference provider (the 3090 box) slots in here later without
touching anything upstream.
"""

from __future__ import annotations

import time
from typing import Protocol


class Provider(Protocol):
    name: str

    def run_batch(self, requests: list[dict]) -> dict[str, str]:
        """requests: [{custom_id, model, system, messages, max_tokens, thinking?}].

        Returns {custom_id: response_text}. Failed requests are simply absent
        from the result — callers must treat the grammar text as the floor.
        """
        ...


class MockProvider:
    """Deterministic offline provider for tests and dry-runs.

    Deliberately emits a statal word ('king') so tests can prove the lexicon
    gate backstop strips unearned vocabulary from model output.
    """

    name = "mock-0"

    def run_batch(self, requests: list[dict]) -> dict[str, str]:
        out = {}
        for r in requests:
            out[r["custom_id"]] = (
                f"[{r['model']}] In the year of which the old ones still speak, "
                f"it happened as the record tells, and the king's shadow lay on no one, "
                f"or on everyone, depending on who sang it."
            )
        return out


class AnthropicBatchProvider:
    """Message Batches against the Claude API.

    Credentials resolve from the environment (ANTHROPIC_API_KEY, or an
    `ant auth login` profile) — construction fails loudly if none are found
    at request time, not at import time.
    """

    name = "anthropic-batch"

    def __init__(self, poll_seconds: int = 20, timeout_seconds: int = 3600) -> None:
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds

    def run_batch(self, requests: list[dict]) -> dict[str, str]:
        import anthropic
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request

        client = anthropic.Anthropic()
        batch_requests = []
        for r in requests:
            params: dict = {
                "model": r["model"],
                "max_tokens": r["max_tokens"],
                "system": r["system"],
                "messages": r["messages"],
            }
            if r.get("thinking") is not None:
                params["thinking"] = r["thinking"]
            batch_requests.append(Request(
                custom_id=r["custom_id"],
                params=MessageCreateParamsNonStreaming(**params)))

        batch = client.messages.batches.create(requests=batch_requests)
        print(f"batch {batch.id}: {len(batch_requests)} requests submitted")

        start = time.time()
        while True:
            batch = client.messages.batches.retrieve(batch.id)
            if batch.processing_status == "ended":
                break
            if time.time() - start > self.timeout_seconds:
                raise TimeoutError(f"batch {batch.id} still {batch.processing_status} "
                                   f"after {self.timeout_seconds}s")
            c = batch.request_counts
            print(f"  …{batch.processing_status}: {c.processing} processing, "
                  f"{c.succeeded} succeeded, {c.errored} errored")
            time.sleep(self.poll_seconds)

        out: dict[str, str] = {}
        errored = 0
        for result in client.messages.batches.results(batch.id):
            if result.result.type == "succeeded":
                msg = result.result.message
                text = next((b.text for b in msg.content if b.type == "text"), "")
                if text:
                    out[result.custom_id] = text
            else:
                errored += 1
        if errored:
            print(f"  {errored} requests failed — grammar text remains their floor")
        return out
