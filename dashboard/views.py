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
    years = [s.year for s in statements]
    revenue = [s.data.get("Revenue", 0) for s in statements]
    net_profit = [s.data.get("NetProfit", 0) for s in statements]
    return render(request, "dashboard/index.html", {"years": years, "revenue": revenue, "net_profit": net_profit})

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