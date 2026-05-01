# Generated — removes orphan whisper_api_key column.
# Whisper STT runs entirely inside each Agent Zero container.
# No central Whisper proxy, no API key needed.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0008_deactivate_legacy_basic_plan"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="tenant",
            name="whisper_api_key",
        ),
    ]
