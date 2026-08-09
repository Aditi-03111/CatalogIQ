import hashlib
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import redis
from sqlmodel import Session, select
from app.core.config import settings
from app.models import CacheEntry, CacheType, CacheStatus

class CacheService:
    def __init__(self, session: Session):
        self.session = session
        # Initialize Redis client, handle connection failures gracefully
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, socket_timeout=1.0, decode_responses=True)
        except Exception:
            self.redis_client = None

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def generate_document_cache_key(self, file_bytes: bytes) -> str:
        doc_hash = hashlib.sha256(file_bytes).hexdigest()
        return f"cache:doc:{doc_hash}"

    def generate_extraction_cache_key(
        self, 
        content_hash: str, 
        model: str, 
        prompt_version: str, 
        schema_version: str = "v1"
    ) -> str:
        raw_key = f"{content_hash}:{model}:{prompt_version}:{schema_version}"
        hashed = self._hash_text(raw_key)
        return f"cache:ext:{hashed}"

    def generate_enrichment_cache_key(
        self, 
        product_data_hash: str, 
        model: str, 
        prompt_version: str
    ) -> str:
        raw_key = f"{product_data_hash}:{model}:{prompt_version}"
        hashed = self._hash_text(raw_key)
        return f"cache:enr:{hashed}"

    def generate_embedding_cache_key(
        self, 
        normalized_content_hash: str, 
        embedding_model: str
    ) -> str:
        raw_key = f"{normalized_content_hash}:{embedding_model}"
        hashed = self._hash_text(raw_key)
        return f"cache:emb:{hashed}"

    def get_cache(self, cache_key: str) -> Optional[str]:
        """
        Attempts to read from Redis first, falling back to PostgreSQL if not found.
        If found in PostgreSQL, re-populates Redis.
        """
        # 1. Ephemeral read check via Redis
        if self.redis_client:
            try:
                cached_val = self.redis_client.get(cache_key)
                if cached_val:
                    return cached_val
            except Exception:
                pass  # Fall back to PostgreSQL if Redis is down/fails

        # 2. Persistent read check via PostgreSQL
        statement = select(CacheEntry).where(
            CacheEntry.cache_key == cache_key,
            CacheEntry.cache_status == CacheStatus.valid
        )
        entry = self.session.exec(statement).first()
        
        if entry:
            # Check expiration
            if entry.expires_at and entry.expires_at < datetime.now(timezone.utc):
                entry.cache_status = CacheStatus.expired
                self.session.add(entry)
                self.session.commit()
                return None
            
            # Reconstruct the Redis ephemeral cache
            if self.redis_client:
                try:
                    # Calculate remaining TTL if applicable
                    ttl = None
                    if entry.expires_at:
                        diff = entry.expires_at - datetime.now(timezone.utc)
                        ttl = int(diff.total_seconds())
                        if ttl <= 0:
                            return None
                    self.redis_client.set(cache_key, entry.result_reference, ex=ttl)
                except Exception:
                    pass
            
            return entry.result_reference
            
        return None

    def set_cache(
        self,
        cache_key: str,
        cache_type: CacheType,
        input_hash: str,
        result_reference: str,
        model: Optional[str] = None,
        prompt_version: Optional[str] = None,
        schema_version: Optional[str] = None,
        pipeline_version: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> CacheEntry:
        """
        Saves cache data into PostgreSQL (source of truth) and Redis (ephemeral speed up).
        """
        # Calculate expiration date
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        # Check if cache entry already exists in PostgreSQL to avoid duplicates
        statement = select(CacheEntry).where(CacheEntry.cache_key == cache_key)
        existing = self.session.exec(statement).first()

        if existing:
            existing.result_reference = result_reference
            existing.cache_status = CacheStatus.valid
            existing.expires_at = expires_at
            if "updated_at" in existing.model_fields:
                existing.updated_at = datetime.now(timezone.utc)
            entry = existing
        else:
            entry = CacheEntry(
                cache_key=cache_key,
                cache_type=cache_type,
                input_hash=input_hash,
                result_reference=result_reference,
                model=model,
                prompt_version=prompt_version,
                schema_version=schema_version,
                pipeline_version=pipeline_version,
                cache_status=CacheStatus.valid,
                expires_at=expires_at
            )
        
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)

        # Populate Redis cache
        if self.redis_client:
            try:
                self.redis_client.set(cache_key, result_reference, ex=ttl_seconds)
            except Exception:
                pass
                
        return entry
