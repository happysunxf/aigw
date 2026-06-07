"""
minimal_ai_gateway.py
一个满足 80% 场景的极简 AI 网关
"""
import asyncio
import hashlib
import time
from typing import Optional
from dataclasses import dataclass
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import numpy as np
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# ====== 1. 配置(可改 YAML)======
PROVIDERS = [
    {"name": "openai",   "url": "https://api.openai.com/v1/chat/completions",
     "key_pool": ["sk-xxx1", "sk-xxx2"], "weight": 1.0,
     "cost_in": 0.15 / 1_000_000, "cost_out": 0.6 / 1_000_000,
     "model_map": {}},
    {"name": "deepseek", "url": "https://api.deepseek.com/v1/chat/completions",
     "key_pool": ["sk-ds1"], "weight": 1.0,
     "cost_in": 0.14 / 1_000_000, "cost_out": 0.28 / 1_000_000,
     "model_map": {
         "gpt-4o-mini": "deepseek-v4-flash",
         "gpt-4o": "deepseek-v4-flash",
         "o1-mini": "deepseek-v4-pro",
         "o1": "deepseek-v4-pro",
     }},
    {"name": "qwen",     "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
     "key_pool": ["sk-qw1"], "weight": 1.0,
     "cost_in": 0.4 / 1_000_000, "cost_out": 0.4 / 1_000_000,
     "model_map": {
         "gpt-4o-mini": "qwen-plus",
         "gpt-4o": "qwen-max",
     }},
]

COOLDOWN_TTL = 30  # 秒
CACHE_THRESHOLD = 0.95
EMBED_DIM = 384

# ====== 2. 冷却存储(内存版,生产用 Redis)======
cooldown_cache: dict[str, float] = {}  # provider_name -> cooldown_until_ts
key_index: dict[str, int] = {p["name"]: 0 for p in PROVIDERS}  # 轮换指针

# ====== 3. OTel + 语义缓存(嵌入用简化版,生产用 bge-small)======
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
tracer = trace.get_tracer(__name__)

# 极简 embedding(实际生产用 bge-small / text-embedding-3-small)
async def embed(text: str) -> np.ndarray:
    h = hashlib.sha256(text.encode()).digest()
    return np.frombuffer(h[:EMBED_DIM], dtype=np.uint8).astype(np.float32) / 255.0

# pgvector 缓存(用 SQLite + 简单哈希近似)
import sqlite3
db = sqlite3.connect("gateway_cache.db", check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE,
    vec BLOB,
    response TEXT,
    ts REAL
)""")
db.commit()

# ====== 4. 网关核心逻辑 ======
app = FastAPI(title="minimal-ai-gateway")

def pick_provider() -> dict:
    """轮询选一个非冷却的 provider"""
    now = time.time()
    candidates = [p for p in PROVIDERS if cooldown_cache.get(p["name"], 0) < now]
    if not candidates:
        candidates = PROVIDERS  # 全部冷却,降级用第一个
    p = candidates[key_index["__round"] % len(candidates)] if "__round" in key_index else candidates[0]
    key_index["__round"] = key_index.get("__round", 0) + 1
    return p

def pick_key(p: dict) -> str:
    """从 key pool 轮换"""
    idx = key_index[p["name"]] % len(p["key_pool"])
    key_index[p["name"]] += 1
    return p["key_pool"][idx]

async def call_provider(p: dict, body: dict, max_retries: int = 2) -> dict:
    """调一次厂商,带重试和厂商 Retry-After 遵循"""
    model_map = p.get("model_map") or {}
    req_model = model_map.get(body.get("model", ""), body.get("model", ""))
    upstream_body = {**body, "model": req_model}
    last_err = None
    for attempt in range(max_retries + 1):
        key = pick_key(p)
        headers = {"Authorization": f"Bearer {key}",
                   "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                if upstream_body.get("stream"):
                    # 流式:返回 StreamingResponse
                    req = client.build_request("POST", p["url"], json=upstream_body, headers=headers)
                    resp = await client.send(req, stream=True)
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("retry-after", 1))
                        await resp.aclose()
                        if attempt < max_retries:
                            await asyncio.sleep(min(retry_after, 10))
                            continue
                    return {"stream": resp}
                else:
                    resp = await client.post(p["url"], json=upstream_body, headers=headers)
                    if resp.status_code in (429, 500, 502, 503, 504):
                        if resp.status_code == 429:
                            retry_after = int(resp.headers.get("retry-after", 1))
                            if attempt < max_retries:
                                await asyncio.sleep(min(retry_after, 10))
                                continue
                        # 标记冷却
                        cooldown_cache[p["name"]] = time.time() + COOLDOWN_TTL
                        last_err = f"status={resp.status_code}"
                        continue
                    return {"json": resp.json(), "status": resp.status_code}
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            cooldown_cache[p["name"]] = time.time() + COOLDOWN_TTL
            last_err = str(e)
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
    raise HTTPException(502, f"all retries failed: {last_err}")

# ====== 5. 语义缓存 ======
async def cache_get(messages: list) -> Optional[dict]:
    """查语义缓存"""
    q = await embed(" ".join(m.get("content", "") for m in messages if isinstance(m, dict)))
    rows = db.execute("SELECT vec, response FROM cache ORDER BY id DESC LIMIT 100").fetchall()
    best, best_sim = None, 0.0
    for vec_blob, resp_json in rows:
        v = np.frombuffer(vec_blob, dtype=np.float32)
        sim = float(np.dot(q, v) / (np.linalg.norm(q) * np.linalg.norm(v) + 1e-9))
        if sim > best_sim:
            best, best_sim = resp_json, sim
    if best_sim >= CACHE_THRESHOLD:
        return {"cached": True, "response": __import__("json").loads(best), "similarity": best_sim}
    return None

async def cache_set(messages: list, response: dict):
    """写语义缓存"""
    q = await embed(" ".join(m.get("content", "") for m in messages if isinstance(m, dict)))
    db.execute("INSERT OR REPLACE INTO cache (key, vec, response, ts) VALUES (?, ?, ?, ?)",
               (hashlib.md5(str(messages).encode()).hexdigest(),
                q.tobytes(), __import__("json").dumps(response), time.time()))
    db.commit()

# ====== 6. FastAPI 路由 ======
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()

    with tracer.start_as_current_span("chat.completion") as span:
        span.set_attribute("gen_ai.system", "minimal-gateway")
        span.set_attribute("gen_ai.request.model", body.get("model", "auto"))

        # 1. 语义缓存查询
        cached = await cache_get(body.get("messages", []))
        if cached:
            span.set_attribute("gen_ai.cache_hit", True)
            span.set_attribute("cache.similarity", cached["similarity"])
            return cached["response"]

        span.set_attribute("gen_ai.cache_hit", False)

        # 2. fallback 链:依次试 provider
        for p in PROVIDERS:
            try:
                result = await call_provider(p, body)
                if "json" in result:
                    # 计算 cost
                    usage = result["json"].get("usage", {})
                    cost_in = usage.get("prompt_tokens", 0) * p["cost_in"]
                    cost_out = usage.get("completion_tokens", 0) * p["cost_out"]
                    span.set_attribute("gen_ai.usage.input_tokens", usage.get("prompt_tokens", 0))
                    span.set_attribute("gen_ai.usage.output_tokens", usage.get("completion_tokens", 0))
                    span.set_attribute("gen_ai.cost.total", cost_in + cost_out)
                    span.set_attribute("gen_ai.routing.chosen_backend", p["name"])
                    # 写缓存(只缓存成功响应,跳过错误)
                    if "choices" in result["json"]:
                        await cache_set(body.get("messages", []), result["json"])
                    return result["json"]
                else:
                    # 流式
                    span.set_attribute("gen_ai.routing.chosen_backend", p["name"])
                    return StreamingResponse(
                        result["stream"].aiter_bytes(),
                        media_type="text/event-stream"
                    )
            except HTTPException as e:
                # 这个 provider 失败,试下一个
                span.add_event(f"provider {p['name']} failed: {e.detail}")
                continue

        raise HTTPException(502, "all providers failed")

# ====== 7. 启动 ======
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)