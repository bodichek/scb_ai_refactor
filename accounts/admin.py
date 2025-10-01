from django.contrib import admin
from .models import CompanyProfile


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
