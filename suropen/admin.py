from django.contrib import admin
from django.utils.html import format_html
from .models import OpenAnswer


@admin.register(OpenAnswer)
class OpenAnswerAdmin(admin.ModelAdmin):
    list_display = ("user", "batch_id", "created_at", "section", "short_question", "short_answer")
    list_filter = ("section", "created_at", "user")
    search_fields = ("question", "answer", "ai_response")
    ordering = ("-created_at",)

    def short_question(self, obj):
        return (obj.question[:50] + "...") if len(obj.question) > 50 else obj.question
    short_question.short_description = "Otázka"

    def short_answer(self, obj):
        return (obj.answer[:50] + "...") if len(obj.answer) > 50 else obj.answer
    short_answer.short_description = "Odpověď"
