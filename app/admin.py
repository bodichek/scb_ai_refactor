from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.template.response import TemplateResponse

from accounts.models import CompanyProfile
from coaching.models import Coach
from ingest.models import Document, FinancialStatement


# ✅ Custom index view – náš dashboard
def custom_index(request):
    companies = CompanyProfile.objects.all()
    coaches_count = Coach.objects.count()
    companies_count = companies.count()
    companies_without_coach = companies.filter(assigned_coach__isnull=True).count()

    rows = []
    for c in companies:
        statements_count = FinancialStatement.objects.filter(owner=c.user).count()

        # klikací odkaz na detail firmy v adminu
        company_link = format_html(
            '<a href="{}">{}</a>',
            reverse("admin:accounts_companyprofile_change", args=[c.id]),
            c.company_name,
        )

        coach_name = (
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:coaching_coach_change", args=[c.assigned_coach.id]),
                c.assigned_coach.user.username,
            )
            if c.assigned_coach else "❌ žádný"
        )

        # poslední dokument (pokud existuje)
        last_doc = Document.objects.filter(owner=c.user).order_by("-year", "-uploaded_at").first()
        last_doc_display = f"{last_doc.year} – {last_doc.doc_type}" if last_doc else "❌ žádný"

        rows.append({
            "company": company_link,
            "ico": c.ico,
            "coach": coach_name,
            "statements": f"{statements_count} výkaz(ů)" if statements_count > 0 else "❌ žádné",
            "last_doc": last_doc_display,
        })

    context = dict(
        companies_count=companies_count,
        coaches_count=coaches_count,
        companies_without_coach=companies_without_coach,
        rows=rows,
        title="Přehled aplikace",
    )
    return TemplateResponse(request, "admin/dashboard.html", context)


# ✅ přepíšeme defaultní index view adminu
admin.site.index = custom_index
