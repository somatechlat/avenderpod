from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from .models import Tenant, Plan
from .vultr_service import deploy_tenant_pod

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
    # 1. Find Plan
    plan = Plan.objects.filter(name__iexact=payload.plan_name).first()
    
    # 2. Create Tenant DB entry
    tenant = Tenant.objects.create(
        name=payload.name,
        email=payload.email,
        plan=plan,
        status='pending'
    )
    
    # 3. Trigger Vultr Deployment
    deploy_tenant_pod(tenant)
    
    return tenant

@router.get("/tenants", response=list[TenantOut])
def list_tenants(request):
    return Tenant.objects.all()

@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    tenant.status = 'suspended'
    tenant.save()
    # In a real scenario, this would call Vultr to stop the Docker container
    return {"message": f"Tenant {tenant.name} suspended."}
