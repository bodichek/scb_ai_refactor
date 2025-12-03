from django.contrib import admin
from django import forms
from django.urls import path
from django.contrib.auth.models import User
from .models import Coach, UserCoachAssignment
from accounts.models import UserRole, CompanyProfile
from django.template.response import TemplateResponse
from coaching.models import Coach
from ingest.models import FinancialStatement


class CoachAdminForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False, label="Jmeno uzivatele")
    last_name = forms.CharField(max_length=150, required=False, label="Prijmeni uzivatele")

    class Meta:
        model = Coach
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name

    def save(self, commit=True):
        coach = super().save(commit=False)
        user = coach.user
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")

        if commit:
            user.save()
            coach.save()
            self.save_m2m()
        return coach


class UserCoachAssignmentInline(admin.TabularInline):
    model = UserCoachAssignment
    extra = 1
    fields = ('client', 'notes', 'assigned_at')
    readonly_fields = ('assigned_at',)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "client":
            # Zobrazit pouze uživatele, kteří NEJSOU coach
            coach_users = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)
            kwargs["queryset"] = User.objects.exclude(id__in=coach_users)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    form = CoachAdminForm
    list_display = (
        "user",
        "specialization",
        "phone",
        "email",
        "city",
        "available",
        "clients_count",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "first_name",
                    "last_name",
                    "specialization",
                    "bio",
                    "phone",
                    "email",
                    "linkedin",
                    "website",
                    "city",
                    "available",
                )
            },
        ),
    )
    list_filter = ("available", "city", "specialization")
    search_fields = ("user__username", "email", "phone", "specialization")
    inlines = [UserCoachAssignmentInline]
    
    def clients_count(self, obj):
        """Počet přiřazených klientů"""
        return UserCoachAssignment.objects.filter(coach=obj).count()
    clients_count.short_description = "Počet klientů"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # zajistí, že uživatel je vždy role "coach"
        UserRole.objects.update_or_create(user=obj.user, defaults={"role": "coach"})


@admin.register(UserCoachAssignment)
class UserCoachAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "coach",
        "client",
        "client_role",
        "assigned_at",
    )
    search_fields = ("coach__user__username", "client__username", "client__email")
    list_filter = ("assigned_at", "coach")
    ordering = ("-assigned_at",)
    
    def client_role(self, obj):
        """Zobrazí roli klienta"""
        try:
            return obj.client.userrole.get_role_display()
        except:
            return "Neznámá"
    client_role.short_description = "Role klienta"
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "client":
            # Zobrazit pouze uživatele, kteří NEJSOU coach
            from accounts.models import UserRole
            coach_users = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)
            kwargs["queryset"] = User.objects.exclude(id__in=coach_users)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
            statements_count = FinancialStatement.objects.filter(user=c.user).count()
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
