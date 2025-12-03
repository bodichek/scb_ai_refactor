from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.template.response import TemplateResponse

from accounts.models import CompanyProfile
from coaching.models import Coach
from ingest.models import Document, FinancialStatement


def custom_index(request):
    companies = CompanyProfile.objects.all()
    coaches_count = Coach.objects.count()
    companies_count = companies.count()
    companies_without_coach = companies.filter(assigned_coach__isnull=True).count()

    rows = []
    for company in companies:
        statements_count = FinancialStatement.objects.filter(user=company.user).count()

        company_link = format_html(
            '<a href="{}">{}</a>',
            reverse("admin:accounts_companyprofile_change", args=[company.id]),
            company.company_name,
        )

        if company.assigned_coach:
            coach_name = format_html(
                '<a href="{}">{}</a>',
                reverse("admin:coaching_coach_change", args=[company.assigned_coach.id]),
                company.assigned_coach.user.username,
            )
        else:
            coach_name = "zadny"

        last_doc = Document.objects.filter(owner=company.user).order_by("-year", "-uploaded_at").first()
        last_doc_display = f"{last_doc.year} - {last_doc.doc_type}" if last_doc else "zadny"

        rows.append({
            "company": company_link,
            "ico": company.ico,
            "coach": coach_name,
            "statements": f"{statements_count} vykaz(u)" if statements_count > 0 else "zadny",
            "last_doc": last_doc_display,
        })

    context = dict(
        companies_count=companies_count,
        coaches_count=coaches_count,
        companies_without_coach=companies_without_coach,
        rows=rows,
        title="Prehled aplikace",
    )
    return TemplateResponse(request, "admin/dashboard.html", context)


admin.site.index = custom_index
