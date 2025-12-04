# Oprava Cash Flow výpočtů - 2024

## Datum: 2024-12-04

## Souhrn změn

Byla provedena kompletní revize a oprava výpočtů Cash Flow, aby odpovídaly správným účetním vzorcům založeným na změnách v rozvaze (Balance Sheet delta calculations).

## Problém

Původní implementace v `dashboard/cashflow.py` používala fixní koeficienty místo skutečných změn v rozvaze:

```python
# ❌ NESPRÁVNĚ - fixní koeficienty
gross_cash_profit = revenue * 0.93 - cogs * 0.98
working_capital_change = revenue * 0.05  # jednoduchý odhad
```

Tyto koeficienty nebyly nikdy specifikovány uživatelem a neodpovídaly skutečným finančním vzorcům.

## Řešení

### 1. Implementace Delta výpočtů z rozvahy

**Nový kód získává data z předchozího roku:**
```python
fs_prev = FinancialStatement.objects.filter(user=user, year=year - 1).first()
balance_prev = (fs_prev.balance or {}) if fs_prev else {}

def _balance_prev_value(keys, default=0.0):
    val = first_number(balance_prev, keys)
    return val if val is not None else default
```

**Výpočet změn (Delta) v rozvaze:**
```python
# Δ Pohledávky, Δ Zásoby, Δ Závazky, Δ Krátkodobé závazky
delta_receivables = receivables - receivables_prev
delta_inventory = inventory - inventory_prev
delta_payables = trade_payables - trade_payables_prev
delta_short_term_liabilities = short_term_liabilities - short_term_liabilities_prev
```

### 2. Správný výpočet Working Capital Change

**Vzorec:**
```
ΔPracovní kapitál = Δ(Zásoby) + Δ(Pohledávky) - Δ(Krátkodobé závazky)
```

**Implementace:**
```python
working_capital_change = (delta_inventory + delta_receivables - delta_short_term_liabilities)
```

**Logika znamének:**
- Vyšší zásoby/pohledávky = cash out (-)
- Vyšší závazky = cash in (+)

### 3. Cash from Customers (Přímá metoda)

**Vzorec:**
```
Cash from Customers = Revenue - Δ(Pohledávky)
```

**Logika:** Pokud pohledávky rostou, zákazníci platili méně, než byly tržby.

**Implementace:**
```python
cash_from_customers = revenue - delta_receivables
```

### 4. Cash to Suppliers (Přímá metoda)

**Vzorec:**
```
Cash to Suppliers = (COGS + služby) + Δ(Zásoby) - Δ(Závazky vůči dodavatelům)
```

**Logika:**
- Vyšší zásoby = nákup navíc = cash out
- Vyšší závazky = zaplatili jsme méně = cash zůstalo

**Implementace:**
```python
cogs_services = _income_value(("cogs_services", "services", "Services"), 0.0)
cash_to_suppliers = (cogs + cogs_services) + delta_inventory - delta_payables
```

### 5. Gross Cash Profit

**Vzorec:**
```
Gross Cash Profit = Cash from Customers - Cash to Suppliers
```

**Implementace:**
```python
gross_cash_profit = cash_from_customers - cash_to_suppliers
```

### 6. Operating Cash Flow (Nepřímá metoda)

**Vzorec:**
```
OCF = Net Profit + Odpisy - ΔPracovního kapitálu
```

**Implementace:**
```python
operating_cf = net_profit + depreciation - working_capital_change
```

## Změněné soubory

### 1. `dashboard/cashflow.py`
- Přidána podpora pro načítání dat z předchozího roku (`fs_prev`)
- Nová funkce `_balance_prev_value()` pro získání hodnot z předchozí rozvahy
- Implementovány delta výpočty pro všechny potřebné položky
- Odstraněny fixní koeficienty (0.93, 0.98, 0.05)
- Implementovány správné vzorce pro všechny Cash Flow komponenty
- Přidány nové návratové hodnoty: `delta_receivables`, `delta_inventory`, `delta_payables`, `delta_short_term_liabilities`

### 2. `test_cashflow.py` (NOVÝ)
- Komplexní testovací soubor pro ověření všech Cash Flow výpočtů
- Mock data pro 2 roky (2023, 2024) s definovanými změnami
- Testy ověřují:
  - Delta výpočty (Δ Receivables, Δ Inventory, Δ Payables, Δ ST Liabilities)
  - Working Capital Change
  - Cash from Customers
  - Cash to Suppliers
  - Gross Cash Profit
  - Operating Cash Flow

**Test výsledky:**
```
Delta Receivables:         500.00 ✓
Delta Inventory:           300.00 ✓
Delta Trade Payables:      300.00 ✓
Delta ST Liabilities:      300.00 ✓
Working Capital Change:    500.00 ✓
Cash from Customers:     23500.00 ✓
Cash to Suppliers:       12800.00 ✓
Gross Cash Profit:       10700.00 ✓
Operating Cash Flow:      5600.00 ✓
```

## Testování

Pro spuštění testů:
```bash
python test_cashflow.py
```

## Verifikované komponenty

Kromě Cash Flow byly také ověřeny další dashboard komponenty:

### Growth metriky (YoY)
- Revenue Growth % = (Revenue_Y - Revenue_{Y-1}) / Revenue_{Y-1} × 100 ✓
- COGS Growth % = (COGS_Y - COGS_{Y-1}) / COGS_{Y-1} × 100 ✓
- Overheads Growth % = (Overheads_Y - Overheads_{Y-1}) / Overheads_{Y-1} × 100 ✓

### Profitability Margins
- Gross Margin % = (Gross Margin / Revenue) × 100 ✓
- Operating Profit % = (EBIT / Revenue) × 100 ✓
- Net Profit % = (Net Profit / Revenue) × 100 ✓

### Dashboard tabulky
- "Přehled dat" - všechny sloupce správně namapovány ✓
- "Zisk vs. peněžní tok" - všechny Cash Flow sekce správně ✓

## Závěr

Všechny Cash Flow výpočty nyní odpovídají standardním účetním vzorcům a používají skutečné změny v rozvaze místo fixních koeficientů. Implementace byla ověřena komplexními testy.

## Spuštění testů

```bash
# Test Cash Flow výpočtů
python test_cashflow.py

# Test všech dashboard komponent (Growth, Profitability)
python test_all_dashboard_components.py

# Test Chart Data (Vision Parser vs Legacy format)
python test_chart_data.py
```

Všechny testy ✅ PASSED.
