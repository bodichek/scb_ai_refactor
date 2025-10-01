from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ingest.models import FinancialStatement

from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import CompanyProfile, UserRole
from coaching.models import UserCoachAssignment
from ingest.models import FinancialStatement

@login_required
def index(request):
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")

    rows = []
    for s in statements:
        rows.append({
            "year": s.year,
            "revenue": s.data.get("Revenue", 0),
            "cogs": s.data.get("COGS", 0),
            "ebit": s.data.get("EBIT", 0),
            "net_profit": s.data.get("NetProfit", 0),
            "gross_margin": s.data.get("GrossMargin", 0),
            "cash": s.data.get("Cash", 0),
            "total_assets": s.data.get("TotalAssets", 0),
            "total_liabilities": s.data.get("TotalLiabilities", 0),
        })

    years = [r["year"] for r in rows]
    revenue = [r["revenue"] for r in rows]
    ebit = [r["ebit"] for r in rows]
    net_profit = [r["net_profit"] for r in rows]

    return render(request, "dashboard/index.html", {
        "statements": statements, # ⬅️ musí se poslat, jinak {% if statements %} bude vždy False
        "rows": rows,
        "years": years,
        "revenue": revenue,
        "ebit": ebit,
        "net_profit": net_profit,
    })

@login_required
def profitability(request):
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    return render(request, "dashboard/profitability.html", {"statements": statements})

@login_required
def report_view(request):
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    return render(request, "dashboard/report.html", {"statements": statements})

@login_required
def dashboard(request):
    role = getattr(request.user.userrole, "role", "company")

    if role == "company":
        # firma → svoje data
        statements = FinancialStatement.objects.filter(owner=request.user)
        company = CompanyProfile.objects.filter(user=request.user).first()
        return render(request, "dashboard/company_dashboard.html", {
            "company": company,
            "statements": statements,
        })

    elif role == "coach":
        # kouč → seznam klientů
        assignments = UserCoachAssignment.objects.filter(coach__user=request.user)
        clients = [a.client for a in assignments]

        selected_client_id = request.GET.get("client")
        if selected_client_id:
            selected_client = get_object_or_404(assignments, client__id=selected_client_id).client
            statements = FinancialStatement.objects.filter(owner=selected_client)
            company = CompanyProfile.objects.filter(user=selected_client).first()
            return render(request, "dashboard/coach_dashboard.html", {
                "clients": clients,
                "selected_client": selected_client,
                "company": company,
                "statements": statements,
            })

        # kouč, ale nevybral ještě klienta
        return render(request, "dashboard/coach_dashboard.html", {
            "clients": clients,
            "statements": [],
            "selected_client": None,
        })