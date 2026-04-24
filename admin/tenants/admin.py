from django.contrib import admin
from .models import Plan, Tenant, VaultRecord, TenantConfig, CatalogItem, InteractionRecord

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_monthly', 'max_conversations')
    search_fields = ('name',)

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'owner', 'plan', 'status', 'assigned_port')
    list_filter = ('status', 'plan')
    search_fields = ('name', 'email')
    readonly_fields = ('vultr_instance_id', 'assigned_port')

@admin.register(VaultRecord)
class VaultRecordAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'vault_path', 'created_at')
    search_fields = ('tenant__name', 'vault_path')
    readonly_fields = ('tenant', 'vault_path', 'description', 'created_at')

@admin.register(TenantConfig)
class TenantConfigAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'key')
    search_fields = ('tenant__name', 'key')

@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'name', 'price')
    list_filter = ('tenant',)
    search_fields = ('name', 'tenant__name')

@admin.register(InteractionRecord)
class InteractionRecordAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'customer_wa_id', 'archetype', 'status', 'created_at')
    list_filter = ('status', 'archetype', 'tenant')
    readonly_fields = ('tenant', 'customer_wa_id', 'archetype', 'status', 'payload', 'created_at')
