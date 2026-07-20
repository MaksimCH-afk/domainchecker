"""Run orchestration for the name classifier (FR-5, FR-8, FR-10, FR-12).

The engine is the whole point of Part 2: the model classifies, the engine
orchestrates — batching, concurrency, retries, cache, incremental persistence,
cancellation and cost accounting. Runs are async tasks so the UI can poll
progress and cancel; every finished batch is persisted immediately (NFR-2).
"""

from __future__ import annotations

import asyncio
import uuid

from .buckets import assign_bucket
from .cost import estimate_cost
from .instruction import SYSTEM_INSTRUCTION, build_user_message
from .normalize import parse_input
from .providers import ProviderError, build_provider
from .schema import Classification, error_result, parse_response
from .store import ClassifierStore


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


class RunManager:
    """Tracks active runs so they can report progress and be cancelled."""

    def __init__(self) -> None:
        self._cancel: dict[str, asyncio.Event] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def is_cancelled(self, run_id: str) -> bool:
        ev = self._cancel.get(run_id)
        return ev.is_set() if ev else False

    def request_cancel(self, run_id: str) -> bool:
        ev = self._cancel.get(run_id)
        if ev:
            ev.set()
            return True
        return False

    def start(self, store: ClassifierStore, text: str, ignore_cache: bool) -> str:
        settings = store.get_settings()
        parsed = parse_input(text)
        run_id = uuid.uuid4().hex
        total = len(parsed.domains) + len(parsed.invalid)
        store.create_run(
            run_id, total=total, provider=settings.get("provider", "openai"),
            model=settings.get("model", ""), batch_api=bool(settings.get("batch_api")),
        )
        store.log(run_id, "INFO",
                  f"Старт: распознано {parsed.recognized}, валидных {len(parsed.domains)}, "
                  f"дублей {parsed.duplicates}, невалидных {len(parsed.invalid)}.")
        self._cancel[run_id] = asyncio.Event()
        self._tasks[run_id] = asyncio.create_task(
            self._run(store, run_id, parsed, settings, ignore_cache)
        )
        return run_id

    async def _run(self, store, run_id, parsed, settings, ignore_cache) -> None:
        state = {"processed": 0, "good": 0, "bad": 0, "review": 0, "errors": 0,
                 "prompt_tokens": 0, "completion_tokens": 0, "est_cost": 0.0}
        threshold = float(settings.get("confidence_threshold", 0.7))
        batch_size = int(settings.get("batch_size", 50))
        concurrency = max(1, int(settings.get("concurrency", 4)))
        max_retries = int(settings.get("max_retries", 3))
        batch_api = bool(settings.get("batch_api"))
        price_in = float(settings.get("price_in_per_1k", 0.0))
        price_out = float(settings.get("price_out_per_1k", 0.0))

        def persist(classifications: list[Classification], run_id=run_id):
            rows = []
            for c in classifications:
                bucket = assign_bucket(c, threshold)
                state[bucket] += 1
                state["processed"] += 1
                rows.append({
                    "domain": c.domain, "original": parsed.original.get(c.domain, c.domain),
                    "bucket": bucket, "verdict": c.verdict, "category": c.category,
                    "name_language": c.name_language, "is_english_name": c.is_english_name,
                    "confidence": c.confidence, "matched_terms": c.matched_terms,
                    "reason": c.reason,
                })
            store.add_results(run_id, rows)
            store.cache_put(rows)
            store.update_run(run_id, **{k: state[k] for k in
                             ("processed", "good", "bad", "review", "errors",
                              "prompt_tokens", "completion_tokens", "est_cost")})

        try:
            # FR-4: invalid domains never go to the model.
            if parsed.invalid:
                persist([error_result(d, "не является доменом")
                         for d in parsed.invalid])

            todo = parsed.domains
            # FR-12: cache hits are not re-sent to the model.
            if not ignore_cache:
                cached = store.cache_get(todo)
                if cached:
                    hits = [Classification(
                        domain=d, verdict=c["verdict"], category=c["category"],
                        name_language=c["name_language"],
                        is_english_name=c["is_english_name"],
                        matched_terms=c["matched_terms"], confidence=c["confidence"],
                        reason=c["reason"]) for d, c in cached.items()]
                    persist(hits)
                    store.log(run_id, "INFO", f"Кэш: {len(hits)} доменов из кэша.")
                    todo = [d for d in todo if d not in cached]

            provider = build_provider(settings)
            sem = asyncio.Semaphore(concurrency)
            batches = list(_chunks(todo, batch_size))

            async def handle(batch: list[str], idx: int):
                if self.is_cancelled(run_id):
                    return
                async with sem:
                    if self.is_cancelled(run_id):
                        return
                    result = await self._classify_batch(
                        store, run_id, provider, batch, max_retries)
                    state["prompt_tokens"] += result["prompt_tokens"]
                    state["completion_tokens"] += result["completion_tokens"]
                    state["est_cost"] = estimate_cost(
                        state["prompt_tokens"], state["completion_tokens"],
                        price_in, price_out, batch_api)
                    persist(result["classifications"])
                    store.log(run_id, "DEBUG",
                              f"Пакет {idx + 1}/{len(batches)} готов ({len(batch)} шт).")

            await asyncio.gather(*(handle(b, i) for i, b in enumerate(batches)))

            status = "cancelled" if self.is_cancelled(run_id) else "done"
            store.update_run(run_id, status=status, finished_at=_now())
            store.log(run_id, "INFO", f"Прогон {status}: обработано {state['processed']}.")
        except ProviderError as e:
            store.update_run(run_id, status="error", finished_at=_now())
            store.log(run_id, "ERROR", f"Провайдер: {e}")
        except Exception as e:  # noqa: BLE001 — never lose the run on an unexpected error
            store.update_run(run_id, status="error", finished_at=_now())
            store.log(run_id, "ERROR", f"Сбой прогона: {e}")
        finally:
            self._cancel.pop(run_id, None)
            self._tasks.pop(run_id, None)

    async def _classify_batch(self, store, run_id, provider, batch, max_retries):
        """One batch with retries (FR-8) and a single reparse retry (FR-10)."""
        user = build_user_message(batch)
        attempt = 0
        while True:
            if self.is_cancelled(run_id):
                return {"classifications": [], "prompt_tokens": 0, "completion_tokens": 0}
            try:
                completion = await provider.complete(SYSTEM_INSTRUCTION, user)
                by_domain = parse_response(completion.content, batch)
                return {
                    "classifications": [by_domain[d] for d in batch],
                    "prompt_tokens": completion.prompt_tokens,
                    "completion_tokens": completion.completion_tokens,
                }
            except ProviderError as e:
                if e.retryable and attempt < max_retries:
                    delay = min(2 ** attempt, 30)
                    store.log(run_id, "DEBUG", f"Ретрай пакета через {delay}s: {e}")
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                store.log(run_id, "ERROR", f"Пакет провалился: {e}")
                return {"classifications": [error_result(d, str(e)) for d in batch],
                        "prompt_tokens": 0, "completion_tokens": 0}
            except ValueError as e:
                # Bad/incomplete JSON: one reparse retry, then mark error (FR-10).
                if attempt < 1:
                    store.log(run_id, "DEBUG", f"Повтор пакета (битый JSON): {e}")
                    attempt += 1
                    continue
                store.log(run_id, "ERROR", f"Схема ответа невалидна: {e}")
                return {"classifications": [error_result(d, "невалидный ответ модели")
                                            for d in batch],
                        "prompt_tokens": 0, "completion_tokens": 0}


def _now() -> float:
    import time
    return time.time()
