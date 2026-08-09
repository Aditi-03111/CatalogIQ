import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlmodel import Session, select
from app.models import Product, ProductVersion, AuditLog, ActorType, ProductStatus

class ProductService:
    def __init__(self, session: Session):
        self.session = session

    def _get_product_snapshot(self, product: Product) -> Dict[str, Any]:
        """
        Builds a complete, reconstructable snapshot dict of the product record.
        """
        return {
            "sku": product.sku,
            "brand": product.brand,
            "product_name": product.product_name,
            "model": product.model,
            "category": product.category,
            "subcategory": product.subcategory,
            "product_type": product.product_type,
            "description": product.description,
            "commerce_description": product.commerce_description,
            "status": product.status,
            "quality_score": product.quality_score,
            "attributes": product.attributes,
            "features": product.features,
            "applications": product.applications,
            "certifications": product.certifications,
            "keywords": product.keywords,
        }

    def create_product(
        self, 
        product_data: Dict[str, Any], 
        actor_type: ActorType = ActorType.system, 
        actor_id: Optional[uuid.UUID] = None
    ) -> Product:
        # Create product
        product = Product(**product_data)
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)

        # Create Version 1 snapshot
        snapshot = self._get_product_snapshot(product)
        version = ProductVersion(
            product_id=product.id,
            version_number=1,
            snapshot=snapshot,
            change_summary="Initial product creation",
            pipeline_version="v1",
            schema_version="v1",
            model_metadata={},
            created_by=actor_type
        )
        self.session.add(version)

        # Create Audit Log
        audit = AuditLog(
            entity_type="product",
            entity_id=product.id,
            action="created",
            actor_type=actor_type,
            actor_id=actor_id,
            before_state=None,
            after_state=snapshot,
            metadata_json={"version_number": 1}
        )
        self.session.add(audit)
        
        self.session.commit()
        self.session.refresh(product)
        return product

    def update_product(
        self,
        product_id: uuid.UUID,
        updated_data: Dict[str, Any],
        change_summary: str = "Product update",
        actor_type: ActorType = ActorType.user,
        actor_id: Optional[uuid.UUID] = None
    ) -> Product:
        product = self.session.get(Product, product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")

        # Capture state before modifications
        before_snapshot = self._get_product_snapshot(product)

        # Apply updates
        for key, val in updated_data.items():
            if hasattr(product, key):
                setattr(product, key, val)
        product.updated_at = datetime.now(timezone.utc)
        self.session.add(product)

        # Get next version number
        stmt = select(ProductVersion).where(ProductVersion.product_id == product_id)
        versions_count = len(list(self.session.exec(stmt).all()))
        next_version = versions_count + 1

        # Save snapshot version
        after_snapshot = self._get_product_snapshot(product)
        version = ProductVersion(
            product_id=product.id,
            version_number=next_version,
            snapshot=after_snapshot,
            change_summary=change_summary,
            pipeline_version="v1",
            schema_version="v1",
            model_metadata={},
            created_by=actor_type
        )
        self.session.add(version)

        # Save Audit Log
        audit = AuditLog(
            entity_type="product",
            entity_id=product.id,
            action="updated",
            actor_type=actor_type,
            actor_id=actor_id,
            before_state=before_snapshot,
            after_state=after_snapshot,
            metadata_json={"version_number": next_version}
        )
        self.session.add(audit)

        self.session.commit()
        self.session.refresh(product)
        return product
