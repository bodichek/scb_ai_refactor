from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from accounts.models import CompanyProfile, Coach, CoachClientNotes
from accounts.permissions import coach_required, can_coach_access_client
from ingest.models import Document
from survey.models import SurveySubmission
from dashboard.cashflow import calculate_cashflow
from .models import Coach


@login_required
@coach_required
def my_clients(request):
    """Dashboard pro kouče - zobrazuje seznam přiřazených klientů"""
    try:
        coach = Coach.objects.get(user=request.user)
        clients = CompanyProfile.objects.filter(assigned_coach=coach).select_related('user')
        
        # Připravíme statistiky pro každého klienta
        clients_data = []
        for client in clients:
            # Počet dokumentů
            statements_count = Document.objects.filter(
                owner=client.user,
                doc_type__in=['income', 'balance', 'rozvaha', 'vysledovka', 'cashflow']
            ).count()
            
            # Poslední aktivita
            last_document = Document.objects.filter(owner=client.user).order_by('-uploaded_at').first()
            last_activity = last_document.uploaded_at if last_document else None
            
            # Přidej statistiky přímo k client objektu
            client.statements_count = statements_count
            client.last_activity = last_activity
            clients_data.append(client)
        
        # Celkové statistiky
        clients_count = len(clients_data)
        active_clients = len([c for c in clients_data if c.last_activity and 
                             c.last_activity > timezone.now() - timedelta(days=30)])
        statements_total = sum(c.statements_count for c in clients_data)
        recent_uploads = Document.objects.filter(
            owner__in=[c.user for c in clients],
            uploaded_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Nedávná aktivita
        recent_activities = []
        recent_docs = Document.objects.filter(
            owner__in=[c.user for c in clients],
            uploaded_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('owner', 'owner__companyprofile').order_by('-uploaded_at')[:5]
        
        for doc in recent_docs:
            recent_activities.append({
                'date': doc.uploaded_at,
                'client_name': doc.owner.companyprofile.company_name,
                'description': f'Nahrál dokument: {doc.get_doc_type_display()}'
            })
        
        context = {
            'clients': clients_data,
            'clients_count': clients_count,
            'active_clients': active_clients,
            'statements_total': statements_total,
            'recent_uploads': recent_uploads,
            'recent_activities': recent_activities
        }
        
        return render(request, 'coaching/my_clients.html', context)
        
    except Coach.DoesNotExist:
        messages.error(request, 'Váš profil kouče nebyl nalezen.')
        return redirect('home')


@login_required
@coach_required
def client_dashboard(request, client_id):
    """Dashboard konkrétního klienta pro kouče"""
    client = get_object_or_404(CompanyProfile, id=client_id)
    
    # Ověřit přístup kouče ke klientovi
    if not can_coach_access_client(request.user, client):
        messages.error(request, 'Nemáte oprávnění k zobrazení tohoto klienta.')
        return redirect('coaching:my_clients')
    
    # Finanční výkazy
    financial_statements = Document.objects.filter(
        owner=client.user,
        doc_type__in=['income', 'balance', 'rozvaha', 'vysledovka', 'cashflow']
    ).order_by('-uploaded_at')
    
    # Ostatní dokumenty
    other_documents = Document.objects.filter(
        owner=client.user
    ).exclude(doc_type__in=['income', 'balance', 'rozvaha', 'vysledovka', 'cashflow']).count()
    
    # Dotazníky
    surveys = SurveySubmission.objects.filter(user=client.user).order_by('-created_at')
    surveys_completed = surveys.count()
    
    # Poslední aktivita
    last_activity = None
    last_document = Document.objects.filter(owner=client.user).order_by('-uploaded_at').first()
    if last_document:
        last_activity = last_document.uploaded_at
        days_since_activity = (timezone.now() - last_activity).days
    else:
        days_since_activity = 999
    
    # Cash Flow data
    has_cashflow_data = False
    cashflow_data = None
    
    try:
        from datetime import datetime
        current_year = datetime.now().year
        cashflow_result = calculate_cashflow(client.user, current_year)
        if cashflow_result:
            has_cashflow_data = True
            cashflow_data = {
                'total_income': cashflow_result.get('revenue', 0),
                'total_expenses': cashflow_result.get('total_operating_expenses', 0),
                'net_cashflow': cashflow_result.get('net_cashflow', 0),
                'months': ['Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen'],
                'income_data': [100000, 120000, 110000, 130000, 125000, 135000],
                'expense_data': [80000, 95000, 85000, 105000, 100000, 110000]
            }
    except Exception as e:
        print(f"Error calculating cashflow: {e}")
    
    # Poznámky kouče
    client_notes = ""
    try:
        coach = Coach.objects.get(user=request.user)
        notes_obj = CoachClientNotes.objects.filter(coach=coach, client=client).first()
        if notes_obj:
            client_notes = notes_obj.notes
    except Coach.DoesNotExist:
        pass
    
    context = {
        'client': client,
        'financial_statements': financial_statements,
        'statements_count': financial_statements.count(),
        'documents_count': other_documents,
        'surveys': surveys,
        'surveys_completed': surveys_completed,
        'days_since_activity': days_since_activity,
        'has_cashflow_data': has_cashflow_data,
        'cashflow': cashflow_data,
        'client_notes': client_notes
    }
    
    return render(request, 'coaching/client_dashboard.html', context)


@login_required
@coach_required
def client_documents(request, client_id):
    """Zobrazení všech dokumentů klienta"""
    client = get_object_or_404(CompanyProfile, id=client_id)
    
    # Ověřit přístup kouče ke klientovi
    if not can_coach_access_client(request.user, client):
        messages.error(request, 'Nemáte oprávnění k zobrazení tohoto klienta.')
        return redirect('coaching:my_clients')
    
    documents = Document.objects.filter(owner=client.user).order_by('-uploaded_at')
    
    context = {
        'client': client,
        'documents': documents
    }
    
    return render(request, 'coaching/client_documents.html', context)


@login_required
@coach_required
def save_client_notes(request, client_id):
    """Uložení poznámek kouče o klientovi"""
    if request.method != 'POST':
        return redirect('coaching:client_dashboard', client_id=client_id)
    
    client = get_object_or_404(CompanyProfile, id=client_id)
    
    # Ověřit přístup kouče ke klientovi
    if not can_coach_access_client(request.user, client):
        messages.error(request, 'Nemáte oprávnění k úpravě poznámek tohoto klienta.')
        return redirect('coaching:my_clients')
    
    try:
        coach = Coach.objects.get(user=request.user)
        notes_text = request.POST.get('notes', '').strip()
        
        notes_obj, created = CoachClientNotes.objects.get_or_create(
            coach=coach,
            client=client,
            defaults={'notes': notes_text}
        )
        
        if not created:
            notes_obj.notes = notes_text
            notes_obj.save()
        
        messages.success(request, 'Poznámky byly úspěšně uloženy.')
        
    except Coach.DoesNotExist:
        messages.error(request, 'Váš profil kouče nebyl nalezen.')
    
    return redirect('coaching:client_dashboard', client_id=client_id)
@login_required
def edit_coach(request):
    coach, _ = Coach.objects.get_or_create(user=request.user)

    if request.method == "POST":
        coach.specialization = request.POST.get("specialization")
        coach.bio = request.POST.get("bio")
        coach.phone = request.POST.get("phone")
        coach.email = request.POST.get("email")
        coach.linkedin = request.POST.get("linkedin")
        coach.website = request.POST.get("website")
        coach.city = request.POST.get("city")
        coach.available = bool(request.POST.get("available"))
        coach.save()
        return redirect("coaching:my_clients")

    return render(request, "coaching/edit_coach.html", {"coach": coach})