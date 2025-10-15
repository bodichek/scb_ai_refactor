from django.urls import path
from . import views
from . import debug_views
from . import test_views

app_name = "chatbot"

urlpatterns = [
    path("api/", views.chat_api, name="chat_api"),
    path("debug/", debug_views.debug_config, name="debug_config"),
    path("test/", test_views.test_page, name="test_page"),
    path("test-api/", test_views.test_openai, name="test_openai"),
]