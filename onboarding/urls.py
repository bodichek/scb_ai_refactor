from django.urls import path

from . import views

app_name = "onboarding"

urlpatterns = [
    path("upload/", views.upload_step, name="upload"),
    path("survey/", views.survey_step, name="survey"),
    path("open-survey/", views.open_survey_step, name="open_survey"),
    path("", views.entrypoint, name="start"),
]
