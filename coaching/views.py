from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.db import models
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
        
        # Získáme search query
        search_query = request.GET.get('search', '').strip()
        
        # Základní queryset - pouze klienti přiřazení tomuto kouči
        clients = CompanyProfile.objects.filter(assigned_coach=coach).select_related('user')
        
        # Pokud je search query, filtrujeme podle názvu firmy nebo jména klienta
        if search_query:
            clients = clients.filter(
                Q(company_name__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        
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
            'recent_activities': recent_activities,
            'search_query': search_query
        }
        
        return render(request, 'coaching/modern_dashboard.html', context)
        
    except Coach.DoesNotExist:
        messages.error(request, 'Váš profil kouče nebyl nalezen.')
        return redirect('home')


@login_required
@coach_required
def client_dashboard(request, client_id):
    """Dashboard konkrétního klienta pro kouče - podporuje AJAX i normální view"""
    client = get_object_or_404(CompanyProfile, id=client_id)
    
    # Ověřit přístup kouče ke klientovi
    if not can_coach_access_client(request.user, client):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Nemáte oprávnění k zobrazení tohoto klienta.'}, status=403)
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
    ).exclude(doc_type__in=['income', 'balance', 'rozvaha', 'vysledovka', 'cashflow']).order_by('-uploaded_at')
    
    # Dotazníky s detailními odpověďmi
    surveys = SurveySubmission.objects.filter(user=client.user).order_by('-created_at')
    surveys_completed = surveys.count()
    
    # Získáme detaily o dotaznících s odpověďmi
    survey_details = []
    for survey in surveys:
        from survey.models import Response
        responses = Response.objects.filter(submission=survey)
        survey_details.append({
            'submission': survey,
            'responses': responses,
            'response_count': responses.count(),
            'avg_score': responses.aggregate(avg_score=Avg('score'))['avg_score'] or 0
        })
    
    # Suropen data - odpovědi klienta
    suropen_answers = []
    try:
        from suropen.models import OpenAnswer
        open_answers = OpenAnswer.objects.filter(user=client.user).order_by('-created_at')
        
        # Seskupíme podle batch_id
        batches = {}
        for answer in open_answers:
            batch_id = str(answer.batch_id)
            if batch_id not in batches:
                batches[batch_id] = {
                    'answers': [],
                    'created_at': answer.created_at,
                    'ai_response': answer.ai_response
                }
            batches[batch_id]['answers'].append(answer)
        
        suropen_answers = list(batches.values())
    except Exception as e:
        print(f"Error loading suropen data: {e}")
    
    # Poslední aktivita
    last_activity = None
    last_document = Document.objects.filter(owner=client.user).order_by('-uploaded_at').first()
    if last_document:
        last_activity = last_document.uploaded_at
        days_since_activity = (timezone.now() - last_activity).days
    else:
        days_since_activity = 999
    
    # Cash Flow data - stejná tabulka jako má klient
    has_cashflow_data = False
    cashflow_data = None
    cashflow_years = []
    
    try:
        from datetime import datetime
        from ingest.models import FinancialStatement
        
        # Získáme všechny roky s finančními daty
        statements = FinancialStatement.objects.filter(owner=client.user).order_by('-year')
        available_years = [stmt.year for stmt in statements]
        
        if available_years:
            # Použijeme nejnovější rok, nebo rok z GET parametru
            selected_year = request.GET.get('year')
            if selected_year and int(selected_year) in available_years:
                current_year = int(selected_year)
            else:
                current_year = available_years[0]  # nejnovější rok
            
            cashflow_result = calculate_cashflow(client.user, current_year)
            if cashflow_result:
                has_cashflow_data = True
                cashflow_data = cashflow_result
                cashflow_years = available_years
    except Exception as e:
        print(f"Error calculating cashflow: {e}")
    
    # Data pro Chart.js grafy - STEJNÉ JAKO MÁ KLIENT na svém dashboardu
    chart_data = []
    table_rows = []
    try:
        from ingest.models import FinancialStatement
        
        statements = FinancialStatement.objects.filter(owner=client.user).order_by('year')
        for s in statements:
            d = s.data or {}

            # Základní výpočty (stejné jako v dashboard/views.py)
            revenue = float(d.get("Revenue", 0))
            cogs = float(d.get("COGS", 0))
            gross_margin = revenue - cogs
            overheads = float(d.get("Overheads", 0))
            depreciation = float(d.get("Depreciation", 0))
            ebit = gross_margin - overheads - depreciation
            net_profit = float(d.get("NetProfit", 0))

            # Růstové ukazatele
            growth_data = {}
            profitability_data = {}
            
            if len(table_rows) > 0:  # Pokud máme předchozí rok
                prev = table_rows[-1]
                growth_data = {
                    'revenue': ((revenue / prev['revenue'] - 1) * 100) if prev['revenue'] > 0 else 0,
                    'cogs': ((cogs / prev['cogs'] - 1) * 100) if prev['cogs'] > 0 else 0,
                    'overheads': ((overheads / prev['overheads'] - 1) * 100) if prev['overheads'] > 0 else 0,
                }
            
            # Ziskovostní ukazatele
            profitability_data = {
                'gm_pct': (gross_margin / revenue * 100) if revenue > 0 else 0,
                'op_pct': (ebit / revenue * 100) if revenue > 0 else 0,
                'np_pct': (net_profit / revenue * 100) if revenue > 0 else 0,
            }

            row_data = {
                'year': s.year,
                'revenue': revenue,
                'cogs': cogs,
                'gross_margin': gross_margin,
                'overheads': overheads,
                'ebit': ebit,
                'net_profit': net_profit,
                'depreciation': depreciation,
                'growth': growth_data,
                'profitability': profitability_data
            }
            
            table_rows.append(row_data)
            chart_data.append(row_data)
            
    except Exception as e:
        print(f"Error loading chart data: {e}")
    
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
        'other_documents': other_documents,
        'documents_count': other_documents.count(),
        'surveys': surveys,
        'surveys_completed': surveys_completed,
        'survey_details': survey_details,
        'suropen_answers': suropen_answers,
        'days_since_activity': days_since_activity,
        'has_cashflow_data': has_cashflow_data,
        'cashflow': cashflow_data,
        'cashflow_years': cashflow_years,
        'chart_data': chart_data,
        'client_notes': client_notes
    }
    
    # Pokud je to AJAX request, vraťme JSON data pro moderní dashboard
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Připravíme data pro JSON response s lepším error handlingem
            json_data = {
                'client': {
                    'id': client.id,
                    'company_name': client.company_name or '',
                    'user': {
                        'first_name': client.user.first_name or '',
                        'last_name': client.user.last_name or '',
                        'email': client.user.email or ''
                    }
                },
                'statements_count': financial_statements.count() if financial_statements else 0,
                'documents_count': other_documents.count() if other_documents else 0,
                'surveys_completed': surveys_completed,
                'days_since_activity': days_since_activity,
                'has_cashflow_data': has_cashflow_data,
            }
            
            # Přidáme cashflow data pouze pokud existují
            if has_cashflow_data and cashflow_data:
                json_data['cashflow'] = {
                    'monthly_data': cashflow_data.get('monthly_data', []),
                    'total_revenue': cashflow_data.get('total_revenue', 0),
                    'total_expenses': cashflow_data.get('total_expenses', 0),
                    'net_cashflow': cashflow_data.get('net_cashflow', 0)
                }
            else:
                json_data['cashflow'] = None
            
            # Přidáme chart data - STEJNÉ JAKO MÁ KLIENT
            if chart_data:
                json_data['chart_data'] = chart_data  # Pošleme celá data pro všechny grafy
                json_data['table_rows'] = table_rows  # Data pro tabulky
            else:
                json_data['chart_data'] = []
                json_data['table_rows'] = []
            
            # Přidáme survey details
            json_data['survey_details'] = []
            for detail in survey_details:
                try:
                    survey_data = {
                        'submission': {
                            'created_at': detail['submission'].created_at.isoformat()
                        },
                        'response_count': detail['response_count'],
                        'avg_score': float(detail['avg_score']),
                        'responses': []
                    }
                    
                    for resp in detail['responses']:
                        try:
                            survey_data['responses'].append({
                                'question': {'text': str(resp.question.text)},
                                'answer_text': str(resp.answer_text or ''),
                                'score': resp.score or 0
                            })
                        except:
                            continue
                            
                    json_data['survey_details'].append(survey_data)
                except:
                    continue
            
            # Přidáme suropen answers
            json_data['suropen_answers'] = []
            for batch in suropen_answers:
                try:
                    batch_data = {
                        'created_at': batch['created_at'].isoformat(),
                        'ai_response': str(batch['ai_response'] or ''),
                        'answers': []
                    }
                    
                    for answer in batch['answers']:
                        try:
                            batch_data['answers'].append({
                                'question': str(answer.question or ''),
                                'answer': str(answer.answer or '')
                            })
                        except:
                            continue
                            
                    json_data['suropen_answers'].append(batch_data)
                except:
                    continue
            
            # Přidáme dokumenty
            json_data['financial_statements'] = []
            for doc in financial_statements:
                try:
                    json_data['financial_statements'].append({
                        'id': doc.id,
                        'get_doc_type_display': str(doc.get_doc_type_display() if hasattr(doc, 'get_doc_type_display') else 'Finanční výkaz'),
                        'description': str(doc.description or ''),
                        'filename': str(doc.filename or ''),
                        'uploaded_at': doc.uploaded_at.isoformat()
                    })
                except:
                    continue
                    
            json_data['other_documents'] = []
            for doc in other_documents:
                try:
                    json_data['other_documents'].append({
                        'id': doc.id,
                        'get_doc_type_display': str(doc.get_doc_type_display() if hasattr(doc, 'get_doc_type_display') else 'Dokument'),
                        'description': str(doc.description or ''),
                        'filename': str(doc.filename or ''),
                        'uploaded_at': doc.uploaded_at.isoformat()
                    })
                except:
                    continue
            
            return JsonResponse(json_data)
            
        except Exception as e:
            print(f"Error in JSON serialization: {e}")
            return JsonResponse({'error': f'Chyba při načítání dat: {str(e)}'}, status=500)
    
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