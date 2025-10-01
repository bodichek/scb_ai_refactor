# survey/urls.py
from django.urls import path
from . import views

app_name = "survey"

urlpatterns = [
    # hlavní dotazník
    path("", views.questionnaire, name="questionnaire"),

    # alias "history" → použije survey_summary
    path("history/", views.survey_summary, name="history"),

    # přehled všech odeslaných dotazníků
    path("summary/", views.survey_summary, name="summary"),

    # detail jednoho konkrétního dotazníku
    path("detail/<uuid:batch_id>/", views.survey_detail, name="detail"),
]
