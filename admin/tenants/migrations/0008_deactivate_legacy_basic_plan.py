from django.db import migrations


def deactivate_legacy_basic_plan(apps, schema_editor):
    plan_model = apps.get_model("tenants", "Plan")
    plan_model.objects.filter(name__iexact="Basic", slug__isnull=True).update(
        slug="legacy-basic",
        is_active=False,
        description="Legacy placeholder plan kept only for historical tenant references.",
        marketing_badge="Legacy",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0007_plan_allow_call_handling_plan_allow_mobile_app_and_more"),
    ]

    operations = [
        migrations.RunPython(deactivate_legacy_basic_plan, migrations.RunPython.noop),
    ]
