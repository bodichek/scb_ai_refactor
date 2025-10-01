from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"   # ✅ namespace

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(
        template_name="accounts/login.html"
    ), name="login"),

    # ⬅️ vlastní logout přes GET
    path("logout/", views.logout_view, name="logout"),

    path("register/", views.register, name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
]