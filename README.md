# Rag_1

Hands-on RAG learning project, focused on per-document access control
(ACL + ABAC) and technical-interview readiness.
Reference architecture: Azure · M365 · Event Hubs · ACL pre-filter
(see `docs/modelagem-acl-e-esquema.md`).

## Layout

- `src/sources/` — single source contract (`base.py`) + regulated-repository
  simulation (`regulado_mock.py`).
- `src/ingestion/` — `resolve_acl.py`: raw source ACL → principals.
- `src/query/` — `expand_principals.py` + `membership.py`: user → principals.
- `db/` — `schema.sql` (source of truth) and `queries/prefiltro.sql`.
- `tests/` — contract, ACL-resolution and principal-expansion tests.

## Running the tests

```powershell
python -m pytest tests\ -v
```

---

## Architecture Decision Records (ADR)

Lean record of *why* each decision was made. Format: context → decision → consequence.

### ADR-001 — Expand groups at query time, not at ingestion

**Context.** Documents are granted to groups (Entra ID, teams). We could expand
group → users at ingestion (fast at query time) or keep the group as a principal
and expand membership at query time.

**Decision.** Ingestion (`resolve_acl.py`) keeps the **group** as a principal.
Membership expansion happens at **query time** (`expand_principals.py`), through
a `MembershipProvider`.

**Consequence.** Membership changes fast; freezing it in the index would leave
someone who left a group with residual access until the next reindex. Query-time
expansion enables revocation within seconds (a short-TTL cache + event
invalidation wrap the provider later, without touching `expand`). Cost: one
membership lookup per query, mitigable with caching.

### ADR-002 — Match ACL by indexable pairs, not by concatenated string

**Context.** The pre-filter must match the user's principals against
`documento_acl`. The naive form concatenates `tipo || ':' || ref` and compares
against a list.

**Decision.** Pass `(principal_tipo, principal_ref)` as **two aligned arrays**
and match column-by-column via `unnest(...) JOIN`, hitting the composite index
`idx_acl_principal (principal_tipo, principal_ref)`.

**Consequence.** Concatenation yields a computed value no index covers — on
500k+ documents that becomes a seq scan. The pair-based form uses an index scan.
Cost: the `expand_principals` output contract carries two arrays instead of a
single list.

### ADR-003 — Keep ABAC (blinding) separate from principal ACL

**Context.** In the regulated sector, holding a read role is not enough: a
*blinded* team must not see *unblinded* data from the same study. This could be
folded into ACL resolution.

**Decision.** `resolve_acl.py` **carries** the ABAC attributes (`estudo_ref`,
`blinding`, `sponsor_ref`) but does **not** decide on them. The
`unblinded × blinded` denial is a **query-time** rule (`prefiltro.sql`).

**Consequence.** Static authorization (who holds the principal) and contextual
authorization (depends on *who is asking*) live in distinct, independently
testable layers. Ingestion stays idempotent. Cost: the blinding rule lives in
the query SQL, not on the document — auditing access needs both.

---

## Known limitations

- **Chunker overlap unit mismatch.** `FixedSizeChunker` takes an injectable
  length function (`comprimento`) that measures the *target* size, but the
  slicing itself still cuts by character index. When a real tokenizer is
  introduced, slicing should cut in the same unit it measures (tokens), so the
  overlap is token-accurate. Deferred on purpose — not adding a tokenizer
  dependency before it is needed.

## Security boundary vs. latency cache

The membership cache (`MembershipCache`, §5) is a **latency optimization, not a
security boundary**. Stale membership is not a leak on its own: a document is
only recoverable if the **index ACL** still grants one of the user's principals.
Two independent layers protect the document — revoking a user's *group
membership* (cache) and revoking the *document's grant* (ACL, via
`eventhub_sync`, §4). The second is what actually closes a document.

Consequence: the cache errs closed. A short TTL (30–60s) bounds how long a stale
entry can live regardless of whether an invalidation event arrives, so removing
users from a group takes effect within the TTL at worst — and instantly if the
document's ACL is revoked by event. No reverse group→users index is needed.

## Evaluation & metrics

The project ships deterministic, LLM-free metrics so quality, cost and latency
can run in CI and be demonstrated on demand.

### Retrieval quality (`src/eval/metrics.py`)
Measured **after the ACL pre-filter** — recall over documents the user cannot see
is meaningless. Metrics: `recall@k` (fraction of relevant chunks in the top-k),
`precision@k` (fraction of the top-k that is relevant), and `MRR` (rank of the
first relevant chunk). Evaluated against a golden set of questions with known
relevant chunk ids.

### Cost (`src/eval/custo.py`)
Context tokens are the dominant, controllable cost in RAG — each retrieved chunk
is paid input. Token counting is injectable: an approximation (~4 chars/token)
for CI, swapped for the real Azure OpenAI tokenizer (`tiktoken`) when absolute
USD is needed. The contract price lives in one place —
`PRECO_INPUT_USD_POR_1K` in `src/config.py` — so editing it updates every cost
calculation. `k` (`TOP_K_DEFAULT`) is the main cost lever: higher k raises recall
and token cost together.

### Latency (`src/eval/latencia.py`)
Reported as **percentiles (p50 / p95 / p99), not average** — the average hides
the tail, and the tail is what breaks an SLA. p50 is the typical case; p99 is the
worst 1%. A p99 drifting away from p50 signals degradation — in production, the
known trigger is an over-selective ACL pre-filter forcing the ANN search to scan
more candidates.

### Demonstration
`python scripts/relatorio_custo_latencia.py` prints cost (from the config price)
and latency percentiles over N searches. Edit the config price, re-run, see the
new figure.

> Note: latency figures from the mock backend are **not representative** of Azure
> AI Search — the mock runs in Python and does not isolate the pre-filter from the
> full search. The module demonstrates the *instrument* (percentiles over samples);
> real numbers require measuring the live service under load.
