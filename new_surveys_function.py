@login_required  
def client_surveys_data(request, client_id):
    """AJAX endpoint pro načtení survey odpovědí klienta"""
    client_user = get_object_or_404(User, id=client_id)
    
    # Ověřit přístup kouče ke klientovi
    if not can_coach_access_client(request.user, client_user):
        return JsonResponse({'error': 'Nemáte oprávnění k tomuto klientovi.'}, status=403)
    
    try:
        # Importujeme survey modely
        from survey.models import SurveySubmission, Response
        
        # Získáme všechny dotazníky klienta
        submissions = SurveySubmission.objects.filter(user=client_user).order_by('-created_at')
        
        html = f"""
        <div class="card">
            <div class="card-header d-flex justify-content-between">
                <h6>📋 Vyplněné dotazníky</h6>
                <span class="badge bg-info">{submissions.count()} dotazníků</span>
            </div>
            <div class="card-body">
        """
        
        if submissions.exists():
            html += f"""
                <div class="alert alert-success mb-3">
                    <strong>📊 Celkem vyplněno:</strong> {submissions.count()} dotazníků
                    <br><small>Poslední vyplnění: {submissions.first().created_at.strftime('%d.%m.%Y %H:%M')}</small>
                </div>
            """
            
            # Projdeme všechny submissions
            for idx, submission in enumerate(submissions):
                # Získáme odpovědi pro toto submission
                responses = Response.objects.filter(submission=submission)
                
                html += f"""
                    <div class="card mb-3">
                        <div class="card-header d-flex justify-content-between">
                            <h6>📝 Dotazník #{submission.batch_id.hex[:8]}</h6>
                            <small class="text-muted">{submission.created_at.strftime('%d.%m.%Y %H:%M')}</small>
                        </div>
                        <div class="card-body">
                """
                
                if responses.exists():
                    html += f"""
                        <div class="alert alert-info mb-3">
                            <strong>📊 Odpovědí:</strong> {responses.count()}
                        </div>
                        
                        <div class="table-responsive">
                            <table class="table table-sm table-striped">
                                <thead>
                                    <tr>
                                        <th>Otázka</th>
                                        <th>Skóre</th>
                                    </tr>
                                </thead>
                                <tbody>
                    """
                    
                    for response in responses:
                        html += f"""
                                    <tr>
                                        <td>{response.question[:80]}{'...' if len(response.question) > 80 else ''}</td>
                                        <td>
                                            <span class="badge bg-{'success' if response.score >= 8 else 'warning' if response.score >= 5 else 'danger'}">
                                                {response.score}/10
                                            </span>
                                        </td>
                                    </tr>
                        """
                    
                    html += """
                                </tbody>
                            </table>
                        </div>
                    """
                    
                    # Přidáme AI response pokud existuje
                    if submission.ai_response:
                        html += f"""
                            <hr>
                            <h6>🤖 AI shrnutí</h6>
                            <div class="alert alert-light">
                                {submission.ai_response[:300]}{'...' if len(submission.ai_response) > 300 else ''}
                            </div>
                        """
                else:
                    html += """
                        <div class="alert alert-warning">
                            <small>Žádné odpovědi nejsou k dispozici.</small>
                        </div>
                    """
                
                html += """
                        </div>
                    </div>
                """
            
            # Přidáme souhrnné statistiky
            total_responses = sum([Response.objects.filter(submission=s).count() for s in submissions])
            html += f"""
                <hr>
                <div class="row mt-3">
                    <div class="col-md-4">
                        <div class="card bg-light">
                            <div class="card-body text-center">
                                <h5>{submissions.count()}</h5>
                                <small>Dotazníků</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card bg-light">
                            <div class="card-body text-center">
                                <h5>{total_responses}</h5>
                                <small>Celkem odpovědí</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card bg-light">
                            <div class="card-body text-center">
                                <h5>{submissions.first().created_at.strftime('%d.%m.%Y')}</h5>
                                <small>Poslední aktivita</small>
                            </div>
                        </div>
                    </div>
                </div>
            """
        else:
            html += """
                <div class="alert alert-warning">
                    <h6>📋 Žádné dotazníky</h6>
                    <p>Klient zatím nevyplnil žádné dotazníky.</p>
                    <hr>
                    <small class="text-muted">
                        💡 Dotazníky se zobrazí poté, co je klient vyplní v sekci "Dotazníky".
                    </small>
                </div>
            """
        
        html += """
            </div>
        </div>
        """
        
        return JsonResponse({
            'html': html,
            'success': True
        })
        
    except Exception as e:
        print(f"ERROR in client_surveys_data: {str(e)}")
        return JsonResponse({
            'html': f'''
            <div class="alert alert-danger">
                <h6>⚠️ Chyba při načítání dotazníků</h6>
                <p>Detail: {str(e)}</p>
            </div>
            ''',
            'success': True
        })