import hashlib
import hmac
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from common.fields import EncryptedJSONField, EncryptedTextField


class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    description = models.TextField(blank=True, default="")
    marketing_badge = models.CharField(max_length=64, blank=True, default="")
    is_custom_priced = models.BooleanField(default=False)
    trial_days = models.IntegerField(default=0)
    trial_message_limit = models.IntegerField(default=0)
    support_level = models.CharField(max_length=64, blank=True, default="standard")

    # Commercial and usage limits
    max_conversations = models.IntegerField(default=500)
    max_numbers = models.IntegerField(default=1)
    max_messages_per_day = models.IntegerField(default=1000)
    max_messages_per_minute = models.IntegerField(default=60)
    max_catalog_items = models.IntegerField(default=500)
    max_transcription_minutes = models.IntegerField(default=120)
    max_storage_mb = models.IntegerField(default=1024)
    max_users = models.IntegerField(default=3)
    max_agent_contexts = models.IntegerField(default=1)

    # Runtime footprint for tenant deployment.
    vultr_plan = models.CharField(max_length=64, default="vc2-2c-4gb")
    a0_image = models.CharField(
        max_length=255, default="avenderpod:latest"
    )
    a0_memory_limit = models.CharField(max_length=16, default="3g")
    a0_cpu_limit = models.CharField(max_length=16, default="2.0")
    a0_memory_reservation = models.CharField(max_length=16, default="1g")
    a0_cpu_reservation = models.CharField(max_length=16, default="1.0")

    # Feature gates
    allow_catalog_upload = models.BooleanField(default=True)
    allow_voice_messages = models.BooleanField(default=True)
    allow_human_handoff = models.BooleanField(default=False)
    allow_creator_override = models.BooleanField(default=True)
    allow_custom_domain = models.BooleanField(default=False)
    allow_integrations = models.BooleanField(default=False)
    allow_mobile_app = models.BooleanField(default=False)
    allow_multichannel = models.BooleanField(default=False)
    allow_outbound_reactivation = models.BooleanField(default=False)
    allow_call_handling = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (
            ("deactivate_plan", "Can deactivate SaaS plan"),
            ("assign_plan", "Can assign SaaS plan to tenant"),
        )

    def __str__(self):
        return self.name


class Tenant(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending Deployment"),
        ("pending_payment", "Pending Payment"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("suspended", "Suspended"),
        ("suspended_limit", "Suspended: Plan Limit"),
        ("suspended_billing", "Suspended: Billing"),
        ("deleted", "Deleted"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    owner_full_name = models.CharField(max_length=255, blank=True, default="")
    owner_phone_e164 = models.CharField(max_length=32, blank=True, default="")
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tenants",
        help_text="Tenant owner for RBAC mapping",
        db_index=True,
    )
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    # Infrastructure details
    vultr_instance_id = models.CharField(
        max_length=100, blank=True, null=True, db_index=True
    )
    docker_container_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Docker container ID for locally deployed tenants",
    )
    deployment_backend = models.CharField(
        max_length=16,
        default="vultr",
        choices=(("docker", "Docker (Local)"), ("vultr", "Vultr (Cloud)")),
        help_text="Which backend deployed this tenant's pod",
    )
    assigned_port = models.IntegerField(blank=True, null=True, unique=True)
    custom_domain = models.CharField(max_length=255, blank=True, null=True)

    # Creator Override (God Mode) logic — PIN stored as PBKDF2 hash
    creator_session_pin_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="PBKDF2 hash of temporary session PIN for God Mode challenge",
    )
    pin_expires_at = models.DateTimeField(blank=True, null=True)

    def set_creator_pin(self, raw_pin: str) -> None:
        """Hash and store a God Mode session PIN."""
        self.creator_session_pin_hash = make_password(raw_pin)

    def check_creator_pin(self, raw_pin: str) -> bool:
        """Verify a God Mode session PIN against the stored hash."""
        if not self.creator_session_pin_hash:
            return False
        return check_password(raw_pin, self.creator_session_pin_hash)

    def clear_creator_pin(self) -> None:
        """Clear the God Mode session PIN after successful verification."""
        self.creator_session_pin_hash = None
        self.pin_expires_at = None

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        permissions = (
            ("suspend_tenant", "Can suspend tenant"),
            ("reactivate_tenant", "Can reactivate tenant"),
            ("deploy_tenant", "Can deploy tenant infrastructure"),
            ("rotate_tenant_secret", "Can rotate tenant secrets"),
            ("view_tenant_usage", "Can view tenant usage"),
        )


class GlobalConfig(models.Model):
    """System-wide configuration for the master orchestrator."""

    key = models.CharField(max_length=100, unique=True)
    value = EncryptedTextField(
        help_text="Encrypted at rest. Stores sensitive config like MASTER_CREATOR_PASSWORD."
    )
    description = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key


class Subscription(models.Model):
    STATUS_CHOICES = (
        ("trialing", "Trialing"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("cancelled", "Cancelled"),
        ("suspended", "Suspended"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="active")
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(blank=True, null=True)
    external_customer_id = models.CharField(max_length=128, blank=True)
    external_subscription_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (
            ("change_subscription_plan", "Can change tenant subscription plan"),
        )

    def __str__(self):
        return f"{self.tenant.name} - {self.plan.name} ({self.status})"


class TenantUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="usage")
    period_start = models.DateTimeField()
    period_end = models.DateTimeField(blank=True, null=True)
    conversations_used = models.IntegerField(default=0)
    messages_used = models.IntegerField(default=0)
    transcription_seconds_used = models.IntegerField(default=0)
    catalog_items_used = models.IntegerField(default=0)
    storage_bytes_used = models.BigIntegerField(default=0)
    last_reported_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("tenant", "period_start")
        indexes = [
            models.Index(fields=["tenant", "period_start"]),
        ]

    def __str__(self):
        return f"{self.tenant.name} usage from {self.period_start:%Y-%m-%d}"


class TenantPlanHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="plan_history"
    )
    old_plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_tenant_assignments",
    )
    new_plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="new_tenant_assignments"
    )
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name}: {self.old_plan} -> {self.new_plan}"


class ServiceCredential(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="service_credentials",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    key_prefix = models.CharField(max_length=12, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    scopes = models.JSONField(default=list, blank=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """HMAC-SHA256 keyed with Django SECRET_KEY for per-deployment salting."""
        from django.conf import settings

        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            raw_key.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        return not self.expires_at or self.expires_at > timezone.now()

    def __str__(self):
        tenant = self.tenant.name if self.tenant else "platform"
        return f"{tenant} - {self.name}"


class AuditEvent(models.Model):
    ACTOR_TYPES = (
        ("user", "User"),
        ("service", "Service"),
        ("system", "System"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_type = models.CharField(max_length=16, choices=ACTOR_TYPES)
    actor_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    actor_service = models.ForeignKey(
        ServiceCredential, on_delete=models.SET_NULL, null=True, blank=True
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100, db_index=True)
    target_type = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["tenant", "created_at"]),
        ]
        permissions = (("view_security_audit", "Can view security audit events"),)

    def __str__(self):
        return f"{self.action} @ {self.created_at:%Y-%m-%d %H:%M:%S}"


class VaultRecord(models.Model):
    """
    Tracks which secrets exist in HashiCorp Vault for a given Tenant.
    The actual secrets are NEVER stored in Postgres.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="vault_records"
    )
    vault_path = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "vault_path")

    def __str__(self):
        return f"{self.tenant.name} - {self.vault_path}"


class TenantConfig(models.Model):
    """Stores key-value onboarding and setup data for the tenant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="configs")
    key = models.CharField(max_length=100)
    value = EncryptedTextField()

    class Meta:
        unique_together = ("tenant", "key")

    def __str__(self):
        return f"{self.tenant.name} - {self.key}"


class CatalogItem(models.Model):
    """Universal catalog (EAV/JSON style) for products/services."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="catalog_items"
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.name} (${self.price})"


class InteractionRecord(models.Model):
    """Universal Interaction Record (Orders, Bookings, Leads)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="interactions"
    )
    customer_wa_id = models.CharField(max_length=50)
    archetype = models.CharField(max_length=50)  # e.g., 'food_order', 'medical_booking'
    status = models.CharField(
        max_length=50
    )  # e.g., 'pending', 'completed', 'cancelled'
    payload = EncryptedJSONField(default=dict)  # PII encrypted at rest
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name} - {self.archetype} ({self.status})"
