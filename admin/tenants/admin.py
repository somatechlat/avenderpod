from django.contrib import admin
from .models import (
    AuditEvent,
    GlobalConfig,
    Plan,
    ServiceCredential,
    Subscription,
    Tenant,
    TenantPlanHistory,
    TenantUsage,
    VaultRecord,
    TenantConfig,
    CatalogItem,
    InteractionRecord,
)


@admin.register(GlobalConfig)
class GlobalConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "description", "updated_at")
    search_fields = ("key",)
    readonly_fields = ("updated_at",)
    # NOTE: 'value' is NOT in list_display to avoid leaking sensitive data.
    # It IS editable in the detail view for authorized superusers.


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "price_monthly",
        "is_custom_priced",
        "max_conversations",
        "max_messages_per_day",
        "vultr_plan",
    )
    list_filter = (
        "is_active",
        "is_custom_priced",
        "allow_voice_messages",
        "allow_multichannel",
        "allow_integrations",
        "allow_creator_override",
    )
    search_fields = ("name", "slug")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "is_active",
                    "price_monthly",
                    "currency",
                    "is_custom_priced",
                    "marketing_badge",
                    "description",
                )
            },
        ),
        (
            "Trial and support",
            {"fields": ("trial_days", "trial_message_limit", "support_level")},
        ),
        (
            "Usage limits",
            {
                "fields": (
                    "max_conversations",
                    "max_numbers",
                    "max_messages_per_day",
                    "max_messages_per_minute",
                    "max_catalog_items",
                    "max_transcription_minutes",
                    "max_storage_mb",
                    "max_users",
                    "max_agent_contexts",
                )
            },
        ),
        (
            "Runtime",
            {
                "fields": (
                    "vultr_plan",
                    "a0_image",
                    "a0_memory_limit",
                    "a0_cpu_limit",
                    "a0_memory_reservation",
                    "a0_cpu_reservation",
                )
            },
        ),
        (
            "Feature gates",
            {
                "fields": (
                    "allow_catalog_upload",
                    "allow_voice_messages",
                    "allow_human_handoff",
                    "allow_creator_override",
                    "allow_custom_domain",
                    "allow_integrations",
                    "allow_mobile_app",
                    "allow_multichannel",
                    "allow_outbound_reactivation",
                    "allow_call_handling",
                )
            },
        ),
    )


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "owner_full_name",
        "owner_phone_e164",
        "owner",
        "plan",
        "status",
        "assigned_port",
    )
    list_filter = ("status", "plan")
    search_fields = ("name", "email")
    readonly_fields = ("vultr_instance_id", "assigned_port")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "plan",
        "status",
        "current_period_start",
        "current_period_end",
    )
    list_filter = ("status", "plan")
    search_fields = ("tenant__name", "external_customer_id", "external_subscription_id")


@admin.register(TenantUsage)
class TenantUsageAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "period_start",
        "conversations_used",
        "messages_used",
        "transcription_seconds_used",
        "last_reported_at",
    )
    list_filter = ("period_start",)
    search_fields = ("tenant__name",)


@admin.register(TenantPlanHistory)
class TenantPlanHistoryAdmin(admin.ModelAdmin):
    list_display = ("tenant", "old_plan", "new_plan", "changed_by", "created_at")
    list_filter = ("new_plan",)
    search_fields = ("tenant__name", "reason")
    readonly_fields = (
        "tenant",
        "old_plan",
        "new_plan",
        "changed_by",
        "reason",
        "created_at",
    )


@admin.register(ServiceCredential)
class ServiceCredentialAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tenant",
        "key_prefix",
        "is_active",
        "last_used_at",
        "expires_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "tenant__name", "key_prefix")
    readonly_fields = ("key_hash", "last_used_at", "created_at")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "actor_type", "actor_user", "tenant", "created_at")
    list_filter = ("actor_type", "action", "created_at")
    search_fields = ("action", "target_type", "target_id", "tenant__name")
    readonly_fields = (
        "actor_type",
        "actor_user",
        "actor_service",
        "tenant",
        "action",
        "target_type",
        "target_id",
        "metadata",
        "ip_address",
        "created_at",
    )


@admin.register(VaultRecord)
class VaultRecordAdmin(admin.ModelAdmin):
    list_display = ("tenant", "vault_path", "created_at")
    search_fields = ("tenant__name", "vault_path")
    readonly_fields = ("tenant", "vault_path", "description", "created_at")


@admin.register(TenantConfig)
class TenantConfigAdmin(admin.ModelAdmin):
    list_display = ("tenant", "key")
    search_fields = ("tenant__name", "key")


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = ("tenant", "name", "price")
    list_filter = ("tenant",)
    search_fields = ("name", "tenant__name")


@admin.register(InteractionRecord)
class InteractionRecordAdmin(admin.ModelAdmin):
    list_display = ("tenant", "customer_wa_id", "archetype", "status", "created_at")
    list_filter = ("status", "archetype", "tenant")
    readonly_fields = (
        "tenant",
        "customer_wa_id",
        "archetype",
        "status",
        "payload",
        "created_at",
    )
