from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import api_views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("login/", views.login_view, name="login"),
    path("api/company-data/", api_views.get_company_data, name="get_company_data"),
]
