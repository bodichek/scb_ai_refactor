from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from accounts.models import CompanyProfile, CoachClientNotes
from accounts.permissions import coach_required, can_coach_access_client
from ingest.models import Document, FinancialStatement
from survey.models import SurveySubmission
from dashboard.cashflow import calculate_cashflow
from dashboard.views import build_dashboard_context
from .models import Coach, UserCoachAssignment


@login_required
@coach_required
def my_clients(request):
    """Dashboard pro kouÄe - zobrazuje seznam pÅ™iÅ™azenÃ½ch klientÅ¯"""
    try:
        coach = Coach.objects.get(user=request.user)
        
        # ZÃ­skÃ¡me search query
        search_query = request.GET.get('search', '').strip()
        
        clients = (
            CompanyProfile.objects
            .filter(
                models.Q(assigned_coach=coach)
                | models.Q(user__usercoachassignment__coach=coach)
            )
            .select_related('user')
            .distinct()
        )
        
        # Pokud je search query, filtrujeme podle nÃ¡zvu firmy nebo jmÃ©na klienta
        if search_query:
            clients = clients.filter(
                Q(company_name__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        
        # PÅ™ipravÃ­me statistiky pro kaÅ¾dÃ©ho klienta
        clients_data = []
        for client in clients:
            # PoÄet dokumentÅ¯
            statements_count = Document.objects.filter(
                owner=client.user,
                doc_type__in=['income', 'balance', 'rozvaha', 'vysledovka', 'cashflow']
            ).count()
            
            # PoslednÃ­ aktivita
            last_document = Document.objects.filter(owner=client.user).order_by('-uploaded_at').first()
            last_activity = last_document.uploaded_at if last_document else None
            
            # PÅ™idej statistiky pÅ™Ã­mo k client objektu
            client.statements_count = statements_count
            client.last_activity = last_activity
            clients_data.append(client)
        
        # CelkovÃ© statistiky
        clients_count = len(clients_data)
        active_clients = len([c for c in clients_data if c.last_activity and 
                             c.last_activity > timezone.now() - timedelta(days=30)])
        statements_total = sum(c.statements_count for c in clients_data)
        recent_uploads = Document.objects.filter(
            owner__in=[c.user for c in clients],
            uploaded_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # NedÃ¡vnÃ¡ aktivita
        recent_activities = []
        recent_docs = Document.objects.filter(
            owner__in=[c.user for c in clients],
            uploaded_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('owner', 'owner__companyprofile').order_by('-uploaded_at')[:5]
        
        for doc in recent_docs:
            recent_activities.append({
                'date': doc.uploaded_at,
                'client_name': doc.owner.companyprofile.company_name,
                'description': f'NahrÃ¡l dokument: {doc.get_doc_type_display()}'
            })
        
        context = {
            'clients': clients_data,
            'clients_count': clients_count,
            'active_clients': active_clients,
            'statements_total': statements_total,
            'recent_uploads': recent_uploads,
            'recent_activities': recent_activities,
            'search_query': search_query,
            'coach_profile': coach,
        }
        
        return render(request, 'coaching/modern_dashboard.html', context)
        
    except Coach.DoesNotExist:
        messages.error(request, 'VÃ¡Å¡ profil kouÄe nebyl nalezen.')
        return redirect('home')


@login_required
@coach_required
def client_dashboard(request, client_id):
    client = get_object_or_404(CompanyProfile, id=client_id)

    if not can_coach_access_client(request.user, client):
        messages.error(request, 'Nemáte oprávnění k zobrazení tohoto klienta.')
        return redirect('coaching:my_clients')

    context = build_dashboard_context(client.user)
    context['is_coach_preview'] = True
    context['preview_client'] = client
    return render(request, 'dashboard/index.html', context)


@login_required
@coach_required
def client_documents(request, client_id):
    client = get_object_or_404(CompanyProfile, id=client_id)
    if not can_coach_access_client(request.user, client):
        messages.error(request, 'Nemáte oprávnění k zobrazení dokumentů tohoto klienta.')
        return redirect('coaching:my_clients')

    documents = Document.objects.filter(owner=client.user).order_by('-uploaded_at')
    return render(request, 'coaching/client_documents.html', {'client': client, 'documents': documents})

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


# === SPA/JSON endpoints and updated notes view ===
@login_required
@coach_required
def save_client_notes(request, client_id):  # override with JSON support
    """UloÅ¾enÃ­ poznÃ¡mek kouÄe pro klienta (HTML form i JSON)."""
    is_json = request.headers.get('Content-Type', '').startswith('application/json') or \
              request.headers.get('Accept', '').startswith('application/json')
    if request.method != 'POST':
        if is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
        return redirect('coaching:client_dashboard', client_id=client_id)

    client = get_object_or_404(CompanyProfile, id=client_id)
    if not can_coach_access_client(request.user, client):
        if is_json:
            return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
        messages.error(request, 'NemÃ¡te oprÃ¡vnÄ›nÃ­ k ÃºpravÄ› poznÃ¡mek tohoto klienta.')
        return redirect('coaching:my_clients')

    try:
        coach = Coach.objects.get(user=request.user)
        if request.headers.get('Content-Type', '').startswith('application/json'):
            import json
            try:
                payload = json.loads((request.body or b'').decode('utf-8') or '{}')
            except Exception:
                return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
            notes_text = str(payload.get('notes', '')).strip()
        else:
            notes_text = str(request.POST.get('notes', '')).strip()

        notes_obj, created = CoachClientNotes.objects.get_or_create(
            coach=coach,
            client=client,
            defaults={'notes': notes_text}
        )
        if not created:
            notes_obj.notes = notes_text
            notes_obj.save()

        if is_json:
            return JsonResponse({'success': True})
        messages.success(request, 'PoznÃ¡mky byly ÃºspÄ›Å¡nÄ› uloÅ¾eny.')
        return redirect('coaching:client_dashboard', client_id=client_id)

    except Coach.DoesNotExist:
        if is_json:
            return JsonResponse({'success': False, 'error': 'Profil kouÄe nenalezen.'}, status=400)
        messages.error(request, 'VÃ¡Å¡ profil kouÄe nebyl nalezen.')
        return redirect('coaching:client_dashboard', client_id=client_id)


@login_required
@coach_required
def client_data(request, client_id):
    client = get_object_or_404(CompanyProfile, id=client_id)
    if not can_coach_access_client(request.user, client):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    latest_doc = Document.objects.filter(owner=client.user).order_by('-uploaded_at').first()
    statements_count = Document.objects.filter(owner=client.user).count()
    return JsonResponse({
        'success': True,
        'client': {
            'id': client.id,
            'name': client.company_name,
            'user_id': client.user.id,
        },
        'stats': {
            'statements_count': statements_count,
            'last_activity': latest_doc.uploaded_at.isoformat() if latest_doc else None,
        }
    })


@login_required
@coach_required
def documents_data(request, client_id):
    client = get_object_or_404(CompanyProfile, id=client_id)
    if not can_coach_access_client(request.user, client):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    docs = Document.objects.filter(owner=client.user).order_by('-uploaded_at')[:25]
    return JsonResponse({
        'success': True,
        'documents': [
            {
                'id': d.id,
                'name': getattr(d.file, 'name', ''),
                'type': d.doc_type,
                'year': d.year,
                'uploaded_at': d.uploaded_at.isoformat() if getattr(d, 'uploaded_at', None) else None,
            } for d in docs
        ]
    })


@login_required
@coach_required
def cashflow_data(request, client_id):
    client = get_object_or_404(CompanyProfile, id=client_id)
    if not can_coach_access_client(request.user, client):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    years = list(FinancialStatement.objects.filter(owner=client.user).values_list('year', flat=True).order_by('-year'))
    if not years:
        return JsonResponse({'success': True, 'available': False})
    year = years[0]
    cf = calculate_cashflow(client.user, year) or {}
    return JsonResponse({'success': True, 'available': True, 'year': year, 'cashflow': cf})


@login_required
@coach_required
def charts_data(request, client_id):
    client = get_object_or_404(CompanyProfile, id=client_id)
    if not can_coach_access_client(request.user, client):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    rows = []
    for fs in FinancialStatement.objects.filter(owner=client.user).order_by('year'):
        d = fs.data or {}
        revenue = float(d.get('Revenue', 0))
        cogs = float(d.get('COGS', 0))
        overheads = float(d.get('Overheads', 0))
        depreciation = float(d.get('Depreciation', 0))
        ebit = float(d.get('EBIT', revenue - cogs - overheads - depreciation))
        rows.append({'year': fs.year, 'revenue': revenue, 'cogs': cogs, 'ebit': ebit})
    return JsonResponse({'success': True, 'series': rows})


@login_required
@coach_required
def surveys_data(request, client_id):
    client = get_object_or_404(CompanyProfile, id=client_id)
    if not can_coach_access_client(request.user, client):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    submissions = SurveySubmission.objects.filter(user=client.user).order_by('-created_at')
    return JsonResponse({'success': True, 'count': submissions.count(), 'latest': submissions.first().created_at.isoformat() if submissions.first() else None})


@login_required
@coach_required
def suropen_data(request, client_id):
    client = get_object_or_404(CompanyProfile, id=client_id)
    if not can_coach_access_client(request.user, client):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    try:
        from suropen.models import OpenAnswer
        count = OpenAnswer.objects.filter(user=client.user).count()
    except Exception:
        count = 0
    return JsonResponse({'success': True, 'count': count})


# ---- SPA endpoints for coach dashboard ----

def _serialize_client_summary(profile, statements_count, last_activity):
    now = timezone.now()
    days_since = (now - last_activity).days if last_activity else None
    return {
        'id': profile.id,
        'company_name': profile.company_name or '',
        'user': {
            'id': profile.user.id,
            'first_name': profile.user.first_name or '',
            'last_name': profile.user.last_name or '',
            'email': profile.user.email or '',
        },
        'statements_count': statements_count,
        'last_activity': last_activity.isoformat() if last_activity else None,
        'days_since_activity': days_since,
    }


@login_required
@coach_required
def my_clients_api(request):
    coach = get_object_or_404(Coach, user=request.user)
    search_query = (request.GET.get('search') or '').strip()

    clients_qs = (
        CompanyProfile.objects
        .filter(
            models.Q(assigned_coach=coach)
            | models.Q(user__usercoachassignment__coach=coach)
        )
        .select_related('user')
        .distinct()
    )
    if search_query:
        clients_qs = clients_qs.filter(
            Q(company_name__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
        )

    clients_payload = []
    owners = []
    for profile in clients_qs:
        owners.append(profile.user)
        statements_count = Document.objects.filter(
            owner=profile.user,
            doc_type__in=['income', 'balance', 'rozvaha', 'vysledovka', 'cashflow'],
        ).count()
        last_document = Document.objects.filter(owner=profile.user).order_by('-uploaded_at').first()
        last_activity = last_document.uploaded_at if last_document else None
        clients_payload.append(_serialize_client_summary(profile, statements_count, last_activity))

    now = timezone.now()
    active_clients = sum(
        1 for item in clients_payload if item['days_since_activity'] is not None and item['days_since_activity'] <= 30
    )
    statements_total = sum(item['statements_count'] for item in clients_payload)
    recent_uploads = Document.objects.filter(
        owner__in=owners,
        uploaded_at__gte=now - timedelta(days=30),
    ).count()

    recent_docs = (
        Document.objects.filter(
            owner__in=owners,
            uploaded_at__gte=now - timedelta(days=7),
        )
        .select_related('owner', 'owner__companyprofile')
        .order_by('-uploaded_at')[:5]
    )
    recent_activities = [
        {
            'date': doc.uploaded_at.isoformat(),
            'client_name': getattr(doc.owner.companyprofile, 'company_name', ''),
            'description': f"NahrÃ¡l dokument: {doc.get_doc_type_display()}" if hasattr(doc, 'get_doc_type_display') else '',
        }
        for doc in recent_docs
    ]

    return JsonResponse({
        'success': True,
        'search_query': search_query,
        'stats': {
            'clients_count': len(clients_payload),
            'active_clients': active_clients,
            'statements_total': statements_total,
            'recent_uploads': recent_uploads,
        },
        'clients': clients_payload,
        'recent_activities': recent_activities,
    })


