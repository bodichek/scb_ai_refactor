from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ingest.models import FinancialStatement
from dashboard.cashflow import calculate_cashflow

@login_required
def debug_cashflow(request):
    """Debug view pro kontrolu cashflow dat"""
    user = request.user
    statements = FinancialStatement.objects.filter(user=user).order_by("year")
    
    debug_info = {
        'user': str(user),
        'statements_count': statements.count(),
        'statements': []
    }
    
    for statement in statements:
        cf_data = calculate_cashflow(user, statement.year)
        debug_info['statements'].append({
            'year': statement.year,
            'income': statement.income,
            'balance': statement.balance,
            'cashflow_calculated': cf_data is not None,
            'cashflow_data': cf_data
        })
    
    # Pro poslední rok
    selected_year = statements.last().year if statements.exists() else None
    if selected_year:
        cf = calculate_cashflow(user, selected_year)
        debug_info['selected_year'] = selected_year
        debug_info['selected_cashflow'] = cf
    
    return JsonResponse(debug_info, indent=2)
