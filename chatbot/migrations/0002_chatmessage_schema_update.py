from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chatbot", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="chatmessage",
            old_name="context",
            new_name="section",
        ),
        migrations.RenameField(
            model_name="chatmessage",
            old_name="created_at",
            new_name="timestamp",
        ),
        migrations.AlterModelOptions(
            name="chatmessage",
            options={"ordering": ["-timestamp"]},
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="role",
            field=models.CharField(
                choices=[
                    ("user", "User"),
                    ("assistant", "Assistant"),
                    ("system", "System"),
                ],
                default="user",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="query_type",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("context", "Context"),
                ],
                default="general",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="context_data",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="chatmessage",
            name="response",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="chatmessage",
            name="section",
            field=models.CharField(
                blank=True,
                help_text="Kontext sekce dashboardu (např. dashboard, ingest).",
                max_length=100,
            ),
        ),
    ]
