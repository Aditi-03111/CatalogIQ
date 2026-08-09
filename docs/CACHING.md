# CatalogIQ Caching Architecture

CatalogIQ implements a content-addressed multi-level caching system designed to minimize processing latency, control API costs, and optimize background worker tasks.

---

## 1. Ephemeral vs. Persistent Cache Roles

CatalogIQ separates caching concerns into two layers:

### Redis (Ephemeral Cache Accelerator)
- **Role**: High-speed, transient cache.
- **Responsibility**: Fast retrieval of active pipeline states and temporary results.
- **Data Longevity**: Ephemeral. May be cleared, flushed, or restart without data loss.

### PostgreSQL (Persistent Cache Registry)
- **Role**: Long-term cache audit and index mapping.
- **Responsibility**: Stores cache metadata entries (`CacheEntry` table) containing unique keys, hashes, status flags, and physical storage references (e.g. S3 paths or JSON files).
- **Data Longevity**: Persistent. Acts as the source of truth.

> [!IMPORTANT]
> If Redis is flushed, the system will reconstruct cache entries from PostgreSQL. On cache request, if the key is not in Redis but exists as `valid` in the PostgreSQL `CacheEntry` table, the service fetches it, writes it back into Redis with appropriate TTL, and returns the cached result (cache reconstruction).

---

## 2. Caching Levels

```
                   [ Incoming Request / Document ]
                                  │
                                  ▼
           Level 1 ──► [ Document Cache (SHA-256) ]
                                  │
                                  ▼
           Level 2 ──► [ OCR / Parsing Cache (File Ref) ]
                                  │
                                  ▼
           Level 3 ──► [ AI Extraction Cache (Content + Prompt + Model) ]
                                  │
                                  ▼
           Level 4 ──► [ Embedding Cache (Normalized Text + Model) ]
                                  │
                                  ▼
           Level 5 ──► [ AI Enrichment Cache (Product Data + Prompt + Model) ]
```

---

## 3. Cache Keys & Calculations

All cache keys are content-addressed using SHA-256 hashing to guarantee that inputs are matched exactly and changes in schema, models, or prompts trigger cache misses automatically.

### Level 1: Document Ingest Cache
- **Scope**: Avoids re-processing duplicate document uploads.
- **Key formula**: `cache:doc:SHA256(file_bytes)`
- **Lookup behavior**: Direct match on SHA-256 hash. Returns existing `Document` entity and `Product` associations.

### Level 2: OCR & Parsing Cache
- **Scope**: Avoids re-running expensive PDF layouts or OCR text extractors.
- **Key formula**: `cache:ocr:SHA256(file_bytes)`
- **Result reference**: Points to physical text/table outputs in file storage.

### Level 3: AI Structuring & Extraction Cache
- **Scope**: Avoids repeating LLM extraction if document text, model, prompt, or target schema remains unchanged.
- **Key formula**: `cache:ext:SHA256(content_hash + model + prompt_version + schema_version)`

### Level 4: Embedding Cache
- **Scope**: Avoids re-generating text embeddings if content or models change.
- **Key formula**: `cache:emb:SHA256(normalized_content_hash + embedding_model)`

### Level 5: AI Enrichment Cache
- **Scope**: Avoids regenerating commerce text/SEO tags if source data, models, or prompt parameters are modified.
- **Key formula**: `cache:enr:SHA256(product_data_hash + model + prompt_version)`

---

## 4. Cache Invalidation & Expiration

Cache entries are invalidated using three primary mechanisms:
1. **Explicit Status Flags**: `cache_status` field on `CacheEntry` can be changed to `expired` or `invalidated` via backend administration panels or pipeline services.
2. **TTL Expiration**: Cache entries can be initialized with an `expires_at` timestamp. Queries matching expired timestamps update the status to `expired` and trigger a cache miss.
3. **Key Drift**: Updating prompt versions, changing models (e.g. `gpt-4o-mini` → `gpt-4o`), or editing product attributes automatically changes the hashed key, creating a cache miss and forcing regeneration.
