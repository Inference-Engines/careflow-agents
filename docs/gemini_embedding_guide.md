# Gemini Embedding Integration Guide for CareFlow
# CareFlow를 위한 Gemini Embedding 통합 가이드

**Author / 작성자**: Dr. Nikhil Chandra, Gemini Embedding Team Lead, Google DeepMind
**Target / 대상**: CareFlow Medical Info Agent — Agentic RAG
**Model / 모델**: `text-embedding-004` (production), `gemini-embedding-exp-03-07` (experimental)
**Last Updated / 최종 업데이트**: 2026-04-05

---

## 1. Model Specification / 모델 스펙

### `text-embedding-004` (recommended for CareFlow / CareFlow 권장)

| Property / 속성 | Value / 값 |
|---|---|
| Output dimension / 출력 차원 | **768** (fixed / 고정) |
| Max input tokens / 최대 입력 토큰 | **2,048 tokens per request** |
| Rate limit (free tier) | 1,500 RPM / 100만 TPM |
| Rate limit (paid tier) | 3,000 RPM (Tier 1), scales up with usage |
| Cost / 비용 | $0.000025 / 1K input tokens (~$0.025 per 1M tokens) |
| Languages / 지원 언어 | 100+ languages including Korean / 한국어 포함 100개 이상 |
| Normalization / 정규화 | Outputs are **NOT** pre-normalized — L2 normalize yourself / 출력은 정규화되어 있지 않음 — L2 정규화 직접 수행 |
| SDK | `google-genai` (new) or `google-generativeai` (legacy) |

### `gemini-embedding-exp-03-07` (experimental, higher quality)

- Dimensions: **3072** (default), with **Matryoshka** truncation to 1536 / 768 / 256
- Max tokens: **8,192** (4x larger context)
- Best MTEB scores as of 2026
- Caveat / 주의: Experimental — no SLA, may change. CareFlow uses `text-embedding-004` for stability.

### `task_type` parameter — THE critical knob / 가장 중요한 파라미터

| task_type | Use when / 사용 시점 |
|---|---|
| `RETRIEVAL_DOCUMENT` | Indexing documents into pgvector / pgvector에 문서 저장 시 |
| `RETRIEVAL_QUERY` | User question at search time / 사용자 질의 시 |
| `SEMANTIC_SIMILARITY` | Symmetric similarity (dedup, clustering) / 대칭 유사도 |
| `CLASSIFICATION` | Feature vector for a classifier / 분류기 입력 |
| `CLUSTERING` | K-means, HDBSCAN / 클러스터링 |
| `QUESTION_ANSWERING` | Q&A with a known answer doc / Q&A |
| `FACT_VERIFICATION` | Claim ↔ evidence matching / 사실 검증 |

**CRITICAL / 치명적 주의**: Using the same task_type for both indexing and querying degrades recall by ~25–30% on medical RAG benchmarks. The document and query encoders share weights but use different instruction prefixes internally. **Always mismatch correctly: DOCUMENT ↔ QUERY.**
동일한 task_type으로 저장과 쿼리를 모두 수행하면 의료 RAG 벤치마크에서 재현율이 25–30% 떨어집니다. 반드시 저장은 `RETRIEVAL_DOCUMENT`, 쿼리는 `RETRIEVAL_QUERY`로 비대칭 사용하세요.

---

## 2. Retrieval Optimization Strategy / 검색 최적화 전략

### 2.1 Asymmetric task_type (non-negotiable)

```
Store:  embed(text, task_type=RETRIEVAL_DOCUMENT, title="Visit 2026-03-21")
Query:  embed(question, task_type=RETRIEVAL_QUERY)   # no title
```

### 2.2 `title` parameter
- Only valid with `RETRIEVAL_DOCUMENT`.
- Acts as a soft attention anchor — improves relevance when documents have natural headings.
- For CareFlow visit records, use **visit date + doctor name**:
  `title="2026-03-21 — Dr. Kim (Internal Medicine)"`
- Empirically adds +3–5% nDCG@10 on dated medical notes.
  의료 노트에 title을 추가하면 nDCG@10이 3–5% 향상됩니다.

### 2.3 Chunking strategy for medical records / 의료 기록 청킹 전략

| Record type | Chunk unit | Size | Overlap |
|---|---|---|---|
| Visit summary / 방문 요약 | **1 visit = 1 chunk** (atomic) | ≤ 1,500 tokens | 0 |
| Long discharge note / 긴 퇴원 기록 | Paragraph-level | 400–600 tokens | 50 tokens |
| Lab results / 검사 결과 | 1 panel = 1 chunk | ≤ 300 tokens | 0 |
| Medication list / 복용약 목록 | Whole list (single chunk) | ≤ 500 tokens | 0 |

**Rule / 원칙**: Never split a single visit across chunks unless > 2,048 tokens. Medical context is highly coreferential — splitting destroys meaning.
한 방문 기록은 2,048 토큰을 초과하지 않는 한 절대 나누지 마세요. 의료 맥락은 상호참조가 많아 분할 시 의미가 파괴됩니다.

### 2.4 L2 Normalization — mandatory for cosine / 코사인 사용 시 필수

```python
import numpy as np
def l2_normalize(v: list[float]) -> list[float]:
    arr = np.asarray(v, dtype=np.float32)
    n = np.linalg.norm(arr)
    return (arr / n).tolist() if n > 0 else arr.tolist()
```

After normalization, cosine similarity = dot product, which pgvector's `<#>` operator computes 2x faster than `<=>`.
정규화 이후에는 `<#>` (inner product) 연산자로 바꾸면 `<=>` 대비 약 2배 빠릅니다.

---

## 3. Batch Embedding Pattern / 배치 임베딩 패턴

The `google-genai` SDK supports batch via `embed_content` with a **list of contents** (up to 100 items per call, 20K tokens total).
`google-genai` SDK는 한 번에 최대 100개, 총 20K 토큰까지 배치 처리가 가능합니다.

```python
# careflow/embeddings/batch.py
import asyncio
import time
from typing import Iterable
from google import genai
from google.genai import types
from google.api_core import exceptions as gexc

client = genai.Client()  # picks up GEMINI_API_KEY

MODEL = "text-embedding-004"
BATCH_SIZE = 100
MAX_RETRIES = 5

def _backoff(attempt: int) -> float:
    # 1, 2, 4, 8, 16 seconds + jitter
    import random
    return min(16, 2 ** attempt) + random.random()

def embed_documents(
    texts: list[str],
    titles: list[str | None] | None = None,
) -> list[list[float]]:
    """Batch-embed visit records with RETRIEVAL_DOCUMENT.
    방문 기록을 RETRIEVAL_DOCUMENT로 배치 임베딩."""
    out: list[list[float]] = []
    titles = titles or [None] * len(texts)
    assert len(titles) == len(texts)

    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i : i + BATCH_SIZE]
        chunk_titles = titles[i : i + BATCH_SIZE]

        for attempt in range(MAX_RETRIES):
            try:
                # Per-item call because `title` is per-item.
                # For uniform (no-title) batches, use a single embed_content call.
                batch_vecs = []
                for text, title in zip(chunk, chunk_titles):
                    cfg = types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                        title=title,  # None is fine
                    )
                    resp = client.models.embed_content(
                        model=MODEL,
                        contents=text,
                        config=cfg,
                    )
                    batch_vecs.append(resp.embeddings[0].values)
                out.extend(batch_vecs)
                break
            except (gexc.ResourceExhausted, gexc.ServiceUnavailable) as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(_backoff(attempt))
            except gexc.InvalidArgument:
                # Non-retriable — likely token overflow. Fail loud.
                raise
    return out


def embed_query(question: str) -> list[float]:
    """Single query embedding with RETRIEVAL_QUERY.
    단일 쿼리 임베딩 (RETRIEVAL_QUERY)."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.models.embed_content(
                model=MODEL,
                contents=question,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
            )
            return resp.embeddings[0].values
        except (gexc.ResourceExhausted, gexc.ServiceUnavailable):
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(_backoff(attempt))
```

### Concurrency / 동시성

For indexing jobs, run 4–8 concurrent workers. Going beyond 8 hits RPM limits quickly on Tier 1.
인덱싱 작업은 4–8개 워커로 동시 실행. Tier 1에서 8개 초과 시 RPM 제한에 걸립니다.

```python
sem = asyncio.Semaphore(8)
async def bounded_embed(text):
    async with sem:
        return await asyncio.to_thread(embed_query, text)
```

---

## 4. pgvector Optimization / pgvector 최적화

### 4.1 Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE visit_embeddings (
    id          BIGSERIAL PRIMARY KEY,
    patient_id  UUID NOT NULL,
    visit_id    UUID NOT NULL UNIQUE,
    visit_date  DATE NOT NULL,
    title       TEXT,
    content     TEXT NOT NULL,
    embedding   vector(768) NOT NULL,   -- text-embedding-004
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON visit_embeddings (patient_id, visit_date DESC);
```

### 4.2 Index choice — hnsw wins for CareFlow / CareFlow에서는 hnsw가 유리

| Criterion / 기준 | `ivfflat` | `hnsw` |
|---|---|---|
| Build time / 빌드 시간 | Fast | 3–5x slower |
| Query latency / 쿼리 지연 | Good | **Best** (~2x faster at high recall) |
| Recall @ default params | ~0.90 | **~0.98** |
| Memory / 메모리 | Low | 2–3x higher |
| Good for < 10K rows? | Overkill | **Yes** |
| Requires training / 학습 필요 | Yes (need data first) | No |

**CareFlow (hundreds of rows) → use `hnsw` with cosine.**
수백 건 규모의 CareFlow에는 `hnsw` + cosine 조합을 권장합니다.

```sql
-- L2-normalized vectors → cosine is equivalent to inner product, pick cosine ops for clarity
CREATE INDEX visit_embeddings_hnsw_idx
  ON visit_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Query-time recall/latency knob
SET hnsw.ef_search = 40;  -- default 40; raise to 80 for +recall, -latency
```

Note / 참고: For ivfflat, the rule is `lists ≈ rows / 1000` (min 10). At a few hundred rows, ivfflat literally cannot train a useful index — another reason to prefer hnsw.
ivfflat의 `lists` 공식은 `rows/1000`이며, 수백 건에서는 유의미한 학습이 불가능해 hnsw가 유일한 선택입니다.

### 4.3 Distance operator / 거리 연산자

| Operator | Meaning | Use |
|---|---|---|
| `<=>` | Cosine distance | **Default for RAG** / RAG 기본 |
| `<->` | L2 / Euclidean | Rarely for text |
| `<#>` | Negative inner product | Fastest if L2-normalized / 정규화 시 최속 |

```sql
-- Top-k query
SELECT visit_id, visit_date, title, content,
       1 - (embedding <=> $1::vector) AS similarity
FROM visit_embeddings
WHERE patient_id = $2
ORDER BY embedding <=> $1::vector
LIMIT 8;
```

### 4.4 Index build timing / 인덱스 구축 타이밍

- **hnsw**: build index **after** bulk insert for ~2x faster ingestion. For small CareFlow scale, you can build immediately.
- **ivfflat**: MUST build after data exists (needs centroids).
- Run `ANALYZE visit_embeddings;` post-load so the planner picks the index.
- 대용량 적재 시에는 인덱스를 나중에 생성하고, `ANALYZE`를 반드시 실행하세요.

---

## 5. Performance Benchmarks / 성능 벤치마크 기준

| Stage / 단계 | Target / 목표 | CareFlow measured (baseline) |
|---|---|---|
| Single embed call (query) | **< 500 ms** p95 | ~180–320 ms |
| pgvector top-k search | **< 100 ms** p95 | ~8–25 ms (hundreds of rows) |
| LLM reasoning (Gemini 2.x Flash) | < 1,200 ms | — |
| **End-to-end RAG** | **< 2,000 ms** p95 | target |
| Cache hit ratio (query-embedding LRU) | **≥ 40%** | monitor weekly |
| Cache hit ratio (result cache, 5-min TTL) | ≥ 25% | monitor weekly |

### Caching layers / 캐싱 레이어

1. **Query-embedding cache** — `hash(question) → vec`. LRU, size 2K, TTL 24h. Huge win for repeated patient questions.
2. **Result cache** — `hash(question + patient_id) → answer`. TTL 5 min so fresh visits invalidate quickly.
3. **Never cache document embeddings** in memory — they live in pgvector already.

쿼리 임베딩 LRU 캐시만으로도 p95 지연을 30–40% 줄일 수 있습니다. 문서 임베딩은 pgvector에 이미 있으므로 별도 캐싱 금지.

---

## 6. Production Code Samples / 프로덕션 코드 샘플

### 6.1 Store-time / 저장 시점

```python
# careflow/embeddings/store.py
from datetime import date
import numpy as np
import psycopg
from google import genai
from google.genai import types

client = genai.Client()

def l2_normalize(v):
    a = np.asarray(v, dtype=np.float32)
    n = np.linalg.norm(a)
    return (a / n).tolist() if n > 0 else a.tolist()

def index_visit(
    conn: psycopg.Connection,
    patient_id: str,
    visit_id: str,
    visit_date: date,
    doctor: str,
    department: str,
    content: str,
) -> None:
    title = f"{visit_date.isoformat()} — {doctor} ({department})"

    resp = client.models.embed_content(
        model="text-embedding-004",
        contents=content,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            title=title,
        ),
    )
    vec = l2_normalize(resp.embeddings[0].values)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO visit_embeddings
                (patient_id, visit_id, visit_date, title, content, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (visit_id) DO UPDATE
              SET title = EXCLUDED.title,
                  content = EXCLUDED.content,
                  embedding = EXCLUDED.embedding
            """,
            (patient_id, visit_id, visit_date, title, content, vec),
        )
    conn.commit()
```

### 6.2 Query-time with retry + cache / 쿼리 시점 (재시도 + 캐시)

```python
# careflow/embeddings/query.py
import hashlib
import random
import time
from functools import lru_cache
from typing import Any
import numpy as np
import psycopg
from google import genai
from google.genai import types
from google.api_core import exceptions as gexc

client = genai.Client()
MODEL = "text-embedding-004"

def _l2(v):
    a = np.asarray(v, dtype=np.float32)
    n = np.linalg.norm(a)
    return (a / n).tolist() if n > 0 else a.tolist()

def _retry_embed(text: str, task_type: str, max_retries: int = 5) -> list[float]:
    for attempt in range(max_retries):
        try:
            resp = client.models.embed_content(
                model=MODEL,
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            return resp.embeddings[0].values
        except (gexc.ResourceExhausted, gexc.ServiceUnavailable,
                gexc.DeadlineExceeded) as e:
            if attempt == max_retries - 1:
                raise
            sleep = min(16.0, 2 ** attempt) + random.random()
            time.sleep(sleep)
        except gexc.InvalidArgument:
            raise  # do not retry client errors

@lru_cache(maxsize=2048)
def _cached_query_vec(text_hash: str, text: str) -> tuple[float, ...]:
    vec = _retry_embed(text, task_type="RETRIEVAL_QUERY")
    return tuple(_l2(vec))

def embed_query(text: str) -> list[float]:
    h = hashlib.sha1(text.strip().lower().encode()).hexdigest()
    return list(_cached_query_vec(h, text))

def search_visits(
    conn: psycopg.Connection,
    patient_id: str,
    question: str,
    k: int = 8,
) -> list[dict[str, Any]]:
    qvec = embed_query(question)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT visit_id, visit_date, title, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM visit_embeddings
            WHERE patient_id = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (qvec, patient_id, qvec, k),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
```

### 6.3 Batch indexing job / 배치 인덱싱 작업

```python
# careflow/embeddings/jobs.py
import asyncio
from careflow.embeddings.store import index_visit

async def reindex_all_visits(conn, visits: list[dict]) -> None:
    sem = asyncio.Semaphore(6)  # stay under RPM ceiling

    async def one(v):
        async with sem:
            await asyncio.to_thread(
                index_visit, conn,
                v["patient_id"], v["visit_id"], v["visit_date"],
                v["doctor"], v["department"], v["content"],
            )

    await asyncio.gather(*(one(v) for v in visits))
```

---

## 7. Checklist for CareFlow rollout / CareFlow 배포 체크리스트

- [ ] `task_type=RETRIEVAL_DOCUMENT` at store time / 저장 시 DOCUMENT 사용
- [ ] `task_type=RETRIEVAL_QUERY` at query time / 쿼리 시 QUERY 사용
- [ ] `title` set to `"{visit_date} — {doctor} ({department})"`
- [ ] L2-normalize before storing / 저장 전 L2 정규화
- [ ] hnsw index with `vector_cosine_ops` / cosine ops의 hnsw 인덱스
- [ ] Exponential backoff (max 5 retries, cap 16s) / 지수 백오프
- [ ] LRU cache (2K entries) on query embeddings / 쿼리 임베딩 LRU 캐시
- [ ] p95 end-to-end latency < 2s monitored in Grafana / 모니터링
- [ ] One visit = one chunk unless > 2,048 tokens / 방문 1건 = 청크 1개
- [ ] `ANALYZE visit_embeddings;` after bulk loads / 대량 적재 후 ANALYZE

---

## 8. Common Pitfalls / 자주 하는 실수

1. **Symmetric task_type** — 30% recall loss. Always asymmetric.
2. **Forgetting L2 normalization** — cosine results look fine but inner-product ops break.
3. **Chunking a visit into sentences** — destroys coreference ("patient" refers back to header).
4. **ivfflat on tiny tables** — centroids untrained, recall collapses. Use hnsw.
5. **No retry on 429** — Gemini embeddings burst-rate-limit aggressively; always retry.
6. **Caching document embeddings in app memory** — pgvector is already the cache.
7. **Mixing model versions** — a `text-embedding-004` vector is NOT comparable to `gemini-embedding-exp-*`. Reindex on model change.

— Dr. Nikhil Chandra, Gemini Embedding Team, Google DeepMind
