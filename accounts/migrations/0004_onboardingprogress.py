from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("survey", "0002_surveysubmission_ai_response"),
        ("accounts", "0003_coachclientnotes"),
    ]

    operations = [
        migrations.CreateModel(
            name="OnboardingProgress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "current_step",
                    models.CharField(
                        choices=[
                            ("upload", "Nahrání PDF"),
                            ("survey", "Dotazník"),
                            ("open_survey", "Otevřený dotazník"),
                            ("done", "Dokončeno"),
                        ],
                        default="upload",
                        max_length=32,
                    ),
                ),
                ("is_completed", models.BooleanField(default=False)),
                ("suropen_batch_id", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "survey_submission",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="onboarding_progresses",
                        to="survey.surveysubmission",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="onboarding_progress",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Onboarding průvodce",
                "verbose_name_plural": "Onboarding průvodci",
            },
        ),
    ]
