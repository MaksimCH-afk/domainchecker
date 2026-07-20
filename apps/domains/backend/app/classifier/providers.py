"""Provider abstraction (FR-6 of TZ-2).

One OpenAI-compatible client (base_url + model + api_key) serves both OpenAI
and OpenRouter; the active provider is chosen in settings. A MockProvider is
included strictly as an offline/test simulator (no network, no keys) — it is a
dev aid, not the product's classification logic (the model does that).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx


@dataclass
class CompletionResult:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ProviderError(Exception):
    """Transient/permanent provider failure; `retryable` drives backoff."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


# OpenAI-compatible base URLs for the two supported providers.
PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


class OpenAICompatProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float = 0.2,
        timeout: float = 90.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    async def complete(self, system: str, user: str) -> CompletionResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.TransportError) as e:
            raise ProviderError(f"network: {e}", retryable=True)

        if resp.status_code == 429 or resp.status_code >= 500:
            raise ProviderError(
                f"HTTP {resp.status_code}: {resp.text[:200]}", retryable=True
            )
        if resp.status_code >= 400:
            raise ProviderError(
                f"HTTP {resp.status_code}: {resp.text[:200]}", retryable=False
            )

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {}) or {}
        return CompletionResult(
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )


class MockProvider:
    """Offline simulator for tests/demo. Deterministic, no network."""

    def __init__(self, model: str = "mock", temperature: float = 0.2):
        self.model = model
        self.temperature = temperature

    async def complete(self, system: str, user: str) -> CompletionResult:
        domains = [ln.strip() for ln in user.splitlines() if "." in ln]
        bad_terms = {
            "casino": "gambling", "bet": "gambling", "porn": "adult",
            "sex": "adult", "pharma": "pharma", "viagra": "pharma",
            "crypto": "crypto_finance", "loan": "crypto_finance",
            "essay": "scam", "replica": "scam", "torrent": "piracy",
        }
        out = []
        for d in domains:
            sld = d.split(".", 1)[0]
            cat, verdict, terms = "clean", "good", []
            for term, c in bad_terms.items():
                if term in sld:
                    cat, verdict, terms = c, "bad", [term]
                    break
            # crude "foreign name" cue for the simulator only
            english = not any(x in sld for x in ("verbesserer", "gazetesi", "obat", "judi"))
            out.append({
                "domain": d, "verdict": verdict, "category": cat,
                "name_language": "en" if english else "xx",
                "is_english_name": english, "matched_terms": terms,
                "confidence": 0.95 if terms else (0.9 if english else 0.85),
                "reason": "mock",
            })
        return CompletionResult(content=json.dumps(out), prompt_tokens=len(user) // 4,
                                completion_tokens=len(out) * 20)


async def verify_key(provider: str, api_key: str, base_url: str = "") -> tuple[bool, str]:
    """Test an API key with a lightweight GET /models call.

    Returns (ok, human-readable message). Used by the Settings "verify" button.
    """
    if provider == "mock":
        return True, "Mock-провайдер: ключ не требуется."
    if not api_key:
        return False, "Ключ не задан."
    url = (base_url or PROVIDER_BASE_URLS.get(provider) or "").rstrip("/")
    if not url:
        return False, f"Неизвестный провайдер '{provider}'."
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
    except (httpx.TimeoutException, httpx.TransportError) as e:
        return False, f"Сеть недоступна: {e}"
    if resp.status_code == 200:
        try:
            n = len(resp.json().get("data", []))
            return True, f"Ключ валиден. Доступно моделей: {n}."
        except Exception:  # noqa: BLE001
            return True, "Ключ валиден."
    if resp.status_code in (401, 403):
        return False, "Ключ отклонён провайдером (401/403). Проверьте значение."
    return False, f"Провайдер вернул HTTP {resp.status_code}."


def build_provider(settings: dict):
    """Instantiate a provider from persisted settings."""
    provider = settings.get("provider", "openai")
    model = settings.get("model", "gpt-5.4-mini")
    temperature = float(settings.get("temperature", 0.2))
    if provider == "mock":
        return MockProvider(model=model, temperature=temperature)

    keys = settings.get("api_keys", {}) or {}
    api_key = keys.get(provider, "")
    if not api_key:
        raise ProviderError(f"нет API-ключа для провайдера '{provider}'", retryable=False)
    base_url = settings.get("base_url") or PROVIDER_BASE_URLS.get(provider)
    if not base_url:
        raise ProviderError(f"неизвестный провайдер '{provider}'", retryable=False)
    return OpenAICompatProvider(
        api_key=api_key, model=model, base_url=base_url, temperature=temperature
    )
