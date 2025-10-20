from django.contrib import admin

from .models import CompanyProfile, OnboardingProgress


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "ico",
        "contact_person",
        "phone",
        "email",
        "industry",
        "employees_count",
        "assigned_coach",
        "created_at",
    )
    list_filter = ("industry", "employees_count", "assigned_coach")
    search_fields = ("company_name", "ico", "contact_person", "email", "phone")
    ordering = ("company_name",)


@admin.register(OnboardingProgress)
class OnboardingProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "current_step", "is_completed", "survey_submission", "suropen_batch_id", "updated_at")
    list_filter = ("current_step", "is_completed")
    search_fields = ("user__username", "user__email")
