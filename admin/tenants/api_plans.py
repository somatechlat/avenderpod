from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from ninja import Router
from ninja.errors import HttpError
from .models import Plan, Tenant
from .schemas import PlanOut, PlanIn, PlanPatch
from .security import check_sysadmin, audit_event, has_platform_perm
from common.messages import get_message

router = Router()

@router.get("/plans", response=list[PlanOut])
def list_plans(request):
    """Retrieve all plans."""
    if not check_sysadmin(request) and not has_platform_perm(request, "tenants.view_plan"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    return list(Plan.objects.all().order_by("price_monthly"))

@router.post("/plans", response=PlanOut)
def create_plan(request, payload: PlanIn):
    """Create a new plan with all rate-limiting and hardware parameters."""
    if not check_sysadmin(request) and not has_platform_perm(request, "tenants.add_plan"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    
    plan = Plan.objects.create(**payload.dict())
    audit_event(request, "plan.created", metadata={"plan_name": plan.name})
    return plan

@router.put("/plans/{plan_id}", response=PlanOut)
def update_plan(request, plan_id: str, payload: PlanPatch):
    """Update an existing plan's parameters."""
    if not check_sysadmin(request) and not has_platform_perm(request, "tenants.change_plan"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    
    plan = get_object_or_404(Plan, id=plan_id)
    update_data = payload.dict(exclude_unset=True)
    for attr, value in update_data.items():
        setattr(plan, attr, value)
    plan.save()
    audit_event(request, "plan.updated", target_id=str(plan.id))
    return plan

@router.patch("/plans/{plan_id}", response=PlanOut)
def patch_plan(request, plan_id: str, payload: PlanPatch):
    """Patch an existing plan's parameters (alias for PUT logic)."""
    return update_plan(request, plan_id, payload)

@router.delete("/plans/{plan_id}")
def delete_plan(request, plan_id: str):
    """Delete a plan if it has no active tenant assignments."""
    if not check_sysadmin(request) and not has_platform_perm(request, "tenants.delete_plan"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    
    plan = get_object_or_404(Plan, id=plan_id)
    if Tenant.objects.filter(plan=plan).exists():
        raise HttpError(400, get_message("ERR_PLAN_IN_USE"))
        
    plan.delete()
    audit_event(request, "plan.deleted", metadata={"plan_name": plan.name})
    return {"ok": True, "message": get_message("SUCCESS_PLAN_DELETED")}
