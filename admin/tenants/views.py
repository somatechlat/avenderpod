from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required(login_url="/login/")
def dashboard(request):
    """Serve the Lit-based System Admin Dashboard. Requires Django auth."""
    return render(request, "tenants/dashboard.html")
