from django.db import migrations


UPLOAD = "upload"
SURVEY = "survey"
OPEN_SURVEY = "open_survey"
DONE = "done"


def seed_onboarding_progress(apps, schema_editor):
    User = apps.get_model("auth", "User")
    OnboardingProgress = apps.get_model("accounts", "OnboardingProgress")
    UserRole = apps.get_model("accounts", "UserRole")
    Document = apps.get_model("ingest", "Document")
    SurveySubmission = apps.get_model("survey", "SurveySubmission")
    OpenAnswer = apps.get_model("suropen", "OpenAnswer")

    role_map = {ur.user_id: ur.role for ur in UserRole.objects.all()}

    for user in User.objects.all():
        progress, _ = OnboardingProgress.objects.get_or_create(user=user)

        role = role_map.get(user.id)
        if user.is_staff or user.is_superuser or role == "coach":
            progress.current_step = DONE
            progress.is_completed = True
            progress.save(update_fields=["current_step", "is_completed", "updated_at"])
            continue

        has_docs = Document.objects.filter(owner_id=user.id).exists()
        has_survey = SurveySubmission.objects.filter(user_id=user.id).exists()
        has_open = OpenAnswer.objects.filter(user_id=user.id).exists()

        if has_docs and has_survey and has_open:
            progress.current_step = DONE
            progress.is_completed = True
        elif has_docs and has_survey:
            progress.current_step = OPEN_SURVEY
        elif has_docs:
            progress.current_step = SURVEY
        else:
            progress.current_step = UPLOAD

        progress.save(update_fields=["current_step", "is_completed", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("ingest", "0005_document_description_document_filename"),
        ("survey", "0002_surveysubmission_ai_response"),
        ("suropen", "0002_alter_openanswer_options"),
        ("accounts", "0004_onboardingprogress"),
    ]

    operations = [
        migrations.RunPython(seed_onboarding_progress, migrations.RunPython.noop),
    ]
