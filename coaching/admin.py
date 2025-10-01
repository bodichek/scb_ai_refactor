from django.contrib import admin
from django.urls import path
from .models import Coach, UserCoachAssignment
from accounts.models import UserRole, CompanyProfile
from django.template.response import TemplateResponse
from coaching.models import Coach
from ingest.models import FinancialStatement


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "specialization",
        "phone",
        "email",
        "city",
        "available",
    )
    list_filter = ("available", "city", "specialization")
    search_fields = ("user__username", "email", "phone", "specialization")
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # zajistí, že uživatel je vždy role "coach"
        UserRole.objects.update_or_create(user=obj.user, defaults={"role": "coach"})


@admin.register(UserCoachAssignment)
class UserCoachAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "coach",
        "client",
        "assigned_at",
    )
    search_fields = ("coach__user__username", "client__username")
    list_filter = ("assigned_at",)
    ordering = ("-assigned_at",)

class CustomAdminSite(admin.AdminSite):
    site_header = "FinApp Administration"
    site_title = "FinApp Admin"
    index_title = "Přehled aplikace"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("dashboard/", self.admin_view(self.dashboard_view), name="admin-dashboard"),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        companies = CompanyProfile.objects.all()
        coaches_count = Coach.objects.count()
        companies_count = companies.count()
        companies_without_coach = companies.filter(assigned_coach__isnull=True).count()

        # tabulka: seznam firem + placeholder indikátor výkazů
        rows = []
        for c in companies:
            statements_count = FinancialStatement.objects.filter(owner=c.user).count()
            rows.append({
                "company": c.company_name,
                "ico": c.ico,
                "coach": c.assigned_coach.user.username if c.assigned_coach else "❌ žádný",
                "statements": f"{statements_count} výkaz(ů)" if statements_count > 0 else "❌ žádné",
            })

        context = dict(
            self.each_context(request),
            companies_count=companies_count,
            coaches_count=coaches_count,
            companies_without_coach=companies_without_coach,
            rows=rows,
        )
        return TemplateResponse(request, "admin/dashboard.html", context)


# přepíšeme defaultní admin site
custom_admin_site = CustomAdminSite(name="custom_admin")