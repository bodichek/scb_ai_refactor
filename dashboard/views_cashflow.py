from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ingest.models import FinancialStatement
from dashboard.cashflow import calculate_cashflow

@login_required
def cashflow_view(request):
    """
    Zobrazí tabulku Profit vs Cash Flow pro zvolený rok.
    """
    user = request.user
    statements = FinancialStatement.objects.filter(user=user).order_by("year")
    years = [s.year for s in statements]

    selected_year = request.GET.get("year")
    if selected_year:
        selected_year = int(selected_year)
    elif years:
        selected_year = years[-1]  # poslední rok

    cf = None
    error = None
    if selected_year:
        try:
            cf = calculate_cashflow(user, selected_year)
        except Exception as e:
            error = str(e)

    context = {
        "years": years,
        "selected_year": selected_year,
        "cf": cf,
        "error": error,
    }
    return render(request, "dashboard/cashflow.html", context)
