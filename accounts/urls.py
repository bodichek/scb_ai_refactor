from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
]
