# Nový cash flow kód pro coaching views
        if statements.exists():
            years = [stmt.year for stmt in statements]
            
            # Selector pro roky
            html += f"""
                <div class="alert alert-success mb-3">
                    <strong>💰 Cash Flow přehled:</strong> {len(years)} období
                    <br><small>Roky: {min(years)} - {max(years)}</small>
                </div>
                
                <!-- Selector pro roky -->
                <div class="mb-3">
                    <label class="form-label">Vyberte rok pro analýzu:</label>
                    <select class="form-select" id="cashflowYearFilter" onchange="showCashflowForYear()">
            """
            
            for year in sorted(years, reverse=True):
                html += f'<option value="{year}" {"selected" if year == years[-1] else ""}>{year}</option>'
            
            html += """
                    </select>
                </div>
                
                <div id="cashflowTableContainer">
            """
            
            # Vygenerujeme tabulky pro všechny roky
            for year in years:
                try:
                    cf = calculate_cashflow(client_user, year)
                    if cf:
                        html += f"""
                            <div class="cashflow-year-data" data-year="{year}" style="{'display: block' if year == years[-1] else 'display: none'}">
                                <h6>📊 Cash Flow výkaz za rok {year}</h6>
                                
                                <div class="table-responsive">
                                    <table class="table table-striped">
                                        <thead class="table-dark">
                                            <tr>
                                                <th>Položka</th>
                                                <th>Profit (Kč)</th>
                                                <th>Cash Flow (Kč)</th>
                                                <th>Variance (Kč)</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td><strong>Hrubá marže</strong></td>
                                                <td>{cf['gross_margin']:,.0f}</td>
                                                <td>{cf['gross_cash_profit']:,.0f}</td>
                                                <td class="{'text-success' if cf['variance']['gross'] > 0 else 'text-danger'}">{cf['variance']['gross']:,.0f}</td>
                                            </tr>
                                            <tr>
                                                <td><strong>Provozní zisk</strong></td>
                                                <td>{cf['operating_cash_profit']:,.0f}</td>
                                                <td>{cf['operating_cash_flow']:,.0f}</td>
                                                <td class="{'text-success' if cf['variance']['operating'] > 0 else 'text-danger'}">{cf['variance']['operating']:,.0f}</td>
                                            </tr>
                                            <tr class="table-info">
                                                <td><strong>Čistý zisk/CF</strong></td>
                                                <td><strong>{cf['net_profit']:,.0f}</strong></td>
                                                <td><strong>{cf['net_cash_flow']:,.0f}</strong></td>
                                                <td class="{'text-success' if cf['variance']['net'] > 0 else 'text-danger'}"><strong>{cf['variance']['net']:,.0f}</strong></td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                                
                                <!-- Detailní cash flow -->
                                <h6 class="mt-4">💼 Detailní Cash Flow komponenty</h6>
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="card">
                                            <div class="card-header bg-success text-white">
                                                <h6>💼 Provozní činnost</h6>
                                            </div>
                                            <div class="card-body">
                                                <table class="table table-sm">
                                                    <tr>
                                                        <td>Čistý zisk</td>
                                                        <td class="text-end">{cf['net_profit']:,.0f} Kč</td>
                                                    </tr>
                                                    <tr>
                                                        <td>+ Odpisy</td>
                                                        <td class="text-end">{cf['depreciation']:,.0f} Kč</td>
                                                    </tr>
                                                    <tr>
                                                        <td>- Změna prac. kapitálu</td>
                                                        <td class="text-end">{cf['working_capital_change']:,.0f} Kč</td>
                                                    </tr>
                                                    <tr class="table-success">
                                                        <td><strong>Provozní CF</strong></td>
                                                        <td class="text-end"><strong>{cf['operating_cf']:,.0f} Kč</strong></td>
                                                    </tr>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div class="col-md-4">
                                        <div class="card">
                                            <div class="card-header bg-info text-white">
                                                <h6>🏭 Investiční činnost</h6>  
                                            </div>
                                            <div class="card-body">
                                                <table class="table table-sm">
                                                    <tr>
                                                        <td>Prodej aktiv</td>
                                                        <td class="text-end">{cf['asset_sales']:,.0f} Kč</td>
                                                    </tr>
                                                    <tr>
                                                        <td>- CapEx</td>
                                                        <td class="text-end">{cf['capex']:,.0f} Kč</td>
                                                    </tr>
                                                    <tr class="table-info">
                                                        <td><strong>Investiční CF</strong></td>
                                                        <td class="text-end"><strong>{cf['investing_cf']:,.0f} Kč</strong></td>
                                                    </tr>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div class="col-md-4">
                                        <div class="card">
                                            <div class="card-header bg-warning text-dark">
                                                <h6>💳 Finanční činnost</h6>
                                            </div>
                                            <div class="card-body">
                                                <table class="table table-sm">
                                                    <tr>
                                                        <td>Nové úvěry</td>
                                                        <td class="text-end">{cf['loans_received']:,.0f} Kč</td>
                                                    </tr>
                                                    <tr>
                                                        <td>- Splátky úvěrů</td>
                                                        <td class="text-end">{cf['loans_repaid']:,.0f} Kč</td>
                                                    </tr>
                                                    <tr>
                                                        <td>- Dividendy</td>
                                                        <td class="text-end">{cf['dividends_paid']:,.0f} Kč</td>
                                                    </tr>
                                                    <tr class="table-warning">
                                                        <td><strong>Finanční CF</strong></td>
                                                        <td class="text-end"><strong>{cf['financing_cf']:,.0f} Kč</strong></td>
                                                    </tr>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Souhrn -->
                                <div class="card mt-3 bg-light">
                                    <div class="card-body">
                                        <div class="row text-center">
                                            <div class="col-md-3">
                                                <h6>💰 Hotovost začátek</h6>
                                                <h5>{cf['cash_begin']:,.0f} Kč</h5>
                                            </div>
                                            <div class="col-md-3">
                                                <h6>🔄 Celková změna</h6>
                                                <h5 class="{'text-success' if cf['net_cash_flow'] > 0 else 'text-danger'}">{cf['net_cash_flow']:,.0f} Kč</h5>
                                            </div>
                                            <div class="col-md-3">
                                                <h6>💰 Hotovost konec</h6>
                                                <h5>{cf['cash_end']:,.0f} Kč</h5>
                                            </div>
                                            <div class="col-md-3">
                                                <h6>📈 CF/Tržby ratio</h6>
                                                <h5>{(cf['operating_cf']/cf['revenue']*100):.1f}%</h5>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        """
                except Exception as ex:
                    html += f"""
                        <div class="cashflow-year-data" data-year="{year}" style="display: none">
                            <div class="alert alert-warning">
                                <h6>⚠️ Chyba pro rok {year}</h6>
                                <p>{str(ex)}</p>
                            </div>
                        </div>
                    """
            
            html += """
                </div>
                
                <script>
                function showCashflowForYear() {
                    const selectedYear = document.getElementById('cashflowYearFilter').value;
                    const yearDivs = document.querySelectorAll('.cashflow-year-data');
                    
                    yearDivs.forEach(div => {
                        if (div.dataset.year === selectedYear) {
                            div.style.display = 'block';
                        } else {
                            div.style.display = 'none';
                        }
                    });
                }
                
                function refreshCashflow() {
                    location.reload();
                }
                </script>
            """