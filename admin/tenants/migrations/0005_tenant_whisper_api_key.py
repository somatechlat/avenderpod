# Generated manually — adds per-tenant Whisper API key for cluster proxy auth

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0004_globalconfig_tenant_creator_session_pin_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="whisper_api_key",
            field=models.CharField(
                max_length=64,
                blank=True,
                null=True,
                help_text="Per-tenant API key for the central Whisper proxy",
            ),
        ),
    ]
