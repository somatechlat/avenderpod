from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from .models import Tenant, Plan
from .vultr_service import deploy_tenant_pod, suspend_tenant_pod, reactivate_tenant_pod

router = Router()

class TenantIn(Schema):
    name: str
    email: str
    plan_name: str

class TenantOut(Schema):
    id: str
    name: str
    email: str
    status: str
    assigned_port: int | None

@router.post("/tenants", response=TenantOut)
def create_tenant(request, payload: TenantIn):
    plan = Plan.objects.filter(name__iexact=payload.plan_name).first()

    tenant = Tenant.objects.create(
        name=payload.name,
        email=payload.email,
        plan=plan,
        status='pending'
    )

    try:
        deploy_tenant_pod(tenant)
    except (EnvironmentError, RuntimeError) as e:
        # If Vultr API key is missing or API fails, tenant stays pending
        tenant.status = 'pending'
        tenant.save()
        return tenant

    return tenant

@router.get("/tenants", response=list[TenantOut])
def list_tenants(request):
    return Tenant.objects.all()

@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        result = suspend_tenant_pod(tenant)
        return {"ok": True, "message": f"Tenant {tenant.name} suspended.", "detail": result}
    except (EnvironmentError, RuntimeError, ValueError) as e:
        # If Vultr API is not available, still mark as suspended in DB
        tenant.status = 'suspended'
        tenant.save()
        return {"ok": True, "message": f"Tenant {tenant.name} marked suspended (infra: {e})."}

@router.post("/tenants/{tenant_id}/reactivate")
def reactivate_tenant(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        result = reactivate_tenant_pod(tenant)
        return {"ok": True, "message": f"Tenant {tenant.name} reactivated.", "detail": result}
    except (EnvironmentError, RuntimeError, ValueError) as e:
        return {"ok": False, "message": f"Failed to reactivate: {e}"}

from .models import CatalogItem, TenantConfig, InteractionRecord

class CatalogItemIn(Schema):
    name: str
    price: float
    description: str | None = None
    metadata: dict | None = None

class CatalogItemOut(Schema):
    id: str
    name: str
    price: float
    description: str | None
    metadata: dict

@router.get("/tenants/{tenant_id}/catalog", response=list[CatalogItemOut])
def list_catalog(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    return tenant.catalog_items.all()

@router.post("/tenants/{tenant_id}/catalog", response=CatalogItemOut)
def create_catalog_item(request, tenant_id: str, payload: CatalogItemIn):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    item = CatalogItem.objects.create(
        tenant=tenant,
        name=payload.name,
        price=payload.price,
        description=payload.description,
        metadata=payload.metadata or {}
    )
    return item

class ConfigIn(Schema):
    key: str
    value: str

@router.get("/tenants/{tenant_id}/config")
def get_tenant_config(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    configs = tenant.configs.all()
    return {c.key: c.value for c in configs}

@router.post("/tenants/{tenant_id}/config")
def set_tenant_config(request, tenant_id: str, payload: ConfigIn):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    config, created = TenantConfig.objects.update_or_create(
        tenant=tenant, key=payload.key,
        defaults={'value': payload.value}
    )
    return {"ok": True, "key": config.key, "value": config.value}
