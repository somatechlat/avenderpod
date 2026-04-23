from django.shortcuts import render

def dashboard(request):
    """Serve the Lit-based System Admin Dashboard."""
    return render(request, 'tenants/dashboard.html')
