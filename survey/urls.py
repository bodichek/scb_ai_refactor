from django.urls import path
from . import views

app_name = "survey"

urlpatterns = [
    # Původní HTML pohledy (kompatibilita)
    path("", views.questionnaire, name="questionnaire"),
    path("history/", views.survey_summary, name="history"),
    path("summary/", views.survey_summary, name="summary"),
    path("detail/<uuid:batch_id>/", views.survey_detail, name="detail"),

    # API pro React frontend
    path("api/questionnaire/", views.questionnaire_api, name="questionnaire_api"),
    path("api/latest/", views.latest_submission_api, name="latest_submission_api"),
    path("api/submissions/", views.submissions_api, name="submissions_api"),
    path("api/submissions/<uuid:batch_id>/", views.submission_detail_api, name="submission_detail_api"),
]
