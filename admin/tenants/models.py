import uuid
from django.db import models

class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    max_conversations = models.IntegerField(default=500)
    max_numbers = models.IntegerField(default=1)
    
    def __str__(self):
        return self.name

class Tenant(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Deployment'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('deleted', 'Deleted'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Infrastructure details
    vultr_instance_id = models.CharField(max_length=100, blank=True, null=True)
    assigned_port = models.IntegerField(blank=True, null=True)
    custom_domain = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class VaultRecord(models.Model):
    """
    Tracks which secrets exist in HashiCorp Vault for a given Tenant.
    The actual secrets are NEVER stored in Postgres.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="vault_records")
    vault_path = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name} - {self.vault_path}"

class TenantConfig(models.Model):
    """Stores key-value onboarding and setup data for the tenant."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="configs")
    key = models.CharField(max_length=100)
    value = models.TextField()

    class Meta:
        unique_together = ('tenant', 'key')

    def __str__(self):
        return f"{self.tenant.name} - {self.key}"

class CatalogItem(models.Model):
    """Universal catalog (EAV/JSON style) for products/services."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="catalog_items")
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.name} (${self.price})"

class InteractionRecord(models.Model):
    """Universal Interaction Record (Orders, Bookings, Leads)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="interactions")
    customer_wa_id = models.CharField(max_length=50)
    archetype = models.CharField(max_length=50)  # e.g., 'food_order', 'medical_booking'
    status = models.CharField(max_length=50)     # e.g., 'pending', 'completed', 'cancelled'
    payload = models.JSONField()                 # JSON data of the interaction
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name} - {self.archetype} ({self.status})"

