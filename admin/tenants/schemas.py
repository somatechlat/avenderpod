from ninja import Schema
from uuid import UUID


class TenantIn(Schema):
    business_name: str
    owner_full_name: str
    owner_email: str
    owner_phone_e164: str
    plan_name: str


class TenantOut(Schema):
    id: UUID
    name: str
    email: str
    owner_full_name: str
    owner_phone_e164: str
    status: str
    assigned_port: int | None
    deployment_backend: str = "vultr"
    docker_container_id: str | None = None
    vultr_instance_id: str | None = None


class CatalogItemIn(Schema):
    name: str
    price: float
    description: str | None = None
    metadata: dict | None = None


class CatalogItemOut(Schema):
    id: UUID
    name: str
    price: float
    description: str | None
    metadata: dict


class ConfigIn(Schema):
    key: str
    value: str


class PlanOut(Schema):
    id: UUID
    name: str
    slug: str | None
    is_active: bool
    price_monthly: float
    currency: str
    description: str
    marketing_badge: str
    is_custom_priced: bool
    trial_days: int
    trial_message_limit: int
    support_level: str
    max_conversations: int
    max_numbers: int
    max_messages_per_day: int
    max_messages_per_minute: int
    max_catalog_items: int
    max_transcription_minutes: int
    max_storage_mb: int
    max_users: int
    max_agent_contexts: int
    vultr_plan: str
    a0_image: str
    a0_memory_limit: str
    a0_cpu_limit: str
    a0_memory_reservation: str
    a0_cpu_reservation: str
    allow_catalog_upload: bool
    allow_voice_messages: bool
    allow_human_handoff: bool
    allow_creator_override: bool
    allow_custom_domain: bool
    allow_integrations: bool
    allow_mobile_app: bool
    allow_multichannel: bool
    allow_outbound_reactivation: bool
    allow_call_handling: bool


class PlanIn(Schema):
    name: str
    slug: str | None = None
    is_active: bool = True
    price_monthly: float
    currency: str = "USD"
    description: str = ""
    marketing_badge: str = ""
    is_custom_priced: bool = False
    trial_days: int = 0
    trial_message_limit: int = 0
    support_level: str = "standard"
    max_conversations: int = 500
    max_numbers: int = 1
    max_messages_per_day: int = 1000
    max_messages_per_minute: int = 60
    max_catalog_items: int = 500
    max_transcription_minutes: int = 120
    max_storage_mb: int = 1024
    max_users: int = 3
    max_agent_contexts: int = 1
    vultr_plan: str = "vc2-2c-4gb"
    a0_image: str = "agent0ai/agent-zero-tenant:latest"
    a0_memory_limit: str = "3g"
    a0_cpu_limit: str = "2.0"
    a0_memory_reservation: str = "1g"
    a0_cpu_reservation: str = "1.0"
    allow_catalog_upload: bool = True
    allow_voice_messages: bool = True
    allow_human_handoff: bool = False
    allow_creator_override: bool = True
    allow_custom_domain: bool = False
    allow_integrations: bool = False
    allow_mobile_app: bool = False
    allow_multichannel: bool = False
    allow_outbound_reactivation: bool = False
    allow_call_handling: bool = False


class PlanPatch(Schema):
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None
    price_monthly: float | None = None
    currency: str | None = None
    description: str | None = None
    marketing_badge: str | None = None
    is_custom_priced: bool | None = None
    trial_days: int | None = None
    trial_message_limit: int | None = None
    support_level: str | None = None
    max_conversations: int | None = None
    max_numbers: int | None = None
    max_messages_per_day: int | None = None
    max_messages_per_minute: int | None = None
    max_catalog_items: int | None = None
    max_transcription_minutes: int | None = None
    max_storage_mb: int | None = None
    max_users: int | None = None
    max_agent_contexts: int | None = None
    vultr_plan: str | None = None
    a0_image: str | None = None
    a0_memory_limit: str | None = None
    a0_cpu_limit: str | None = None
    a0_memory_reservation: str | None = None
    a0_cpu_reservation: str | None = None
    allow_catalog_upload: bool | None = None
    allow_voice_messages: bool | None = None
    allow_human_handoff: bool | None = None
    allow_creator_override: bool | None = None
    allow_custom_domain: bool | None = None
    allow_integrations: bool | None = None
    allow_mobile_app: bool | None = None
    allow_multichannel: bool | None = None
    allow_outbound_reactivation: bool | None = None
    allow_call_handling: bool | None = None


class TenantUsageOut(Schema):
    tenant_id: str
    period_start: str
    conversations_used: int
    messages_used: int
    transcription_seconds_used: int
    catalog_items_used: int
    storage_bytes_used: int


class TenantUsageIn(Schema):
    conversations_used: int = 0
    messages_used: int = 0
    transcription_seconds_used: int = 0
    catalog_items_used: int = 0
    storage_bytes_used: int = 0


class VaultRecordOut(Schema):
    id: UUID
    tenant_name: str
    vault_path: str
    created_at: str


class InteractionRecordOut(Schema):
    id: UUID
    tenant_name: str
    customer_wa_id: str
    archetype: str
    status: str
    created_at: str


class ChallengeIn(Schema):
    tenant_id: str
    password: str
    pin: str


class PendingChallengeOut(Schema):
    tenant_id: str
    tenant_name: str
    pin: str
    expires_at: str


class TenantStatusOut(Schema):
    tenant_id: str
    tenant_name: str
    status: str
    container_status: str
    last_heartbeat: str | None
    stt_available: bool
    assigned_port: int | None


class DeploymentModeIn(Schema):
    mode: str  # "docker" or "vultr"
