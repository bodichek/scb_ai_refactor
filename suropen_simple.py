        if open_answers.exists():
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
            
            html += f"""
                <div class="alert alert-success mb-3">
                    <strong>🏢 Suropen přehled:</strong> 
                    {open_answers.count()} odpovědí ve {len(batches)} batchích
                </div>
            """
            
            for batch_id, batch_data in batches.items():
                answers = batch_data['answers']
                created_at = batch_data['created_at']
                ai_response = batch_data['ai_response']
                
                html += f"""
                    <div class="card mb-3">
                        <div class="card-header d-flex justify-content-between">
                            <h6>🏢 Batch #{batch_id[:8]}</h6>
                            <small class="text-muted">{created_at.strftime('%d.%m.%Y %H:%M')}</small>
                        </div>
                        <div class="card-body">
                """
                
                # Seskupíme podle sekcí
                sections = {}
                for answer in answers:
                    section = answer.section
                    if section not in sections:
                        sections[section] = []
                    sections[section].append(answer)
                
                for section, section_answers in sections.items():
                    html += f"""
                        <h6>📋 {section}</h6>
                        <div class="table-responsive mb-3">
                            <table class="table table-sm table-striped">
                                <thead>
                                    <tr>
                                        <th>Otázka</th>
                                        <th>Odpověď</th>
                                    </tr>
                                </thead>
                                <tbody>
                    """
                    
                    for answer in section_answers:
                        short_answer = answer.answer[:100] + "..." if len(answer.answer) > 100 else answer.answer
                        html += f"""
                                    <tr>
                                        <td><strong>{answer.question}</strong></td>
                                        <td>{short_answer}</td>
                                    </tr>
                        """
                    
                    html += """
                                </tbody>
                            </table>
                        </div>
                    """
                
                # Přidáme AI response pokud existuje
                if ai_response:
                    html += f"""
                        <hr>
                        <h6>🤖 AI analýza</h6>
                        <div class="alert alert-info">
                            {ai_response[:500]}{'...' if len(ai_response) > 500 else ''}
                        </div>
                    """
                
                html += """
                        </div>
                    </div>
                """