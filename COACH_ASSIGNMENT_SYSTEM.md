# Systém přiřazování Coach-Client

## Přehled
Implementoval jsem nový systém pro przřazování koučů k běžným uživatelům přes Django admin rozhraní.

## Jak to funguje

### 1. Django Admin - Správa přiřazení
- V Django admin (/admin/) najdete sekci "Coaching"
- **Coach**: Zde můžete upravovat profily koučů a vidět počet jejich klientů
- **User coach assignments**: Zde můžete přímo přiřazovat uživatele koučům

### 2. Přiřazování v Coach profilu
- Otevřte konkrétního kouče v admin rozhraní
- Ve spodní části najdete sekci "User coach assignment"
- Můžete přidat nové přiřazení klientů přímo zde
- Systém automaticky zobrazuje pouze ne-coach uživatele

### 3. Coach Dashboard
- Coach se přihlásí s emailem (např. brona.klus@gmail.com)
- V navigaci uvidí menu "Coaching"
- Dashboard zobrazuje pouze přiřazené klienty
- Může si prohlížet jejich dokumenty, grafy a data

## Aktuální stav

### Přiřazení pro brona.klus@gmail.com
Kouč `brona.klus@gmail.com` má aktuálně přiřazené tyto klienty:
- test_client
- client@example.com

### Testování
1. Přihlašte se jako admin do /admin/
2. Jděte do Coaching → User coach assignments
3. Přidejte nové přiřazení kouč → klient
4. Přihlašte se jako kouč na /coaching/my_clients/
5. Ověřte, že vidí pouze své přiřazené klienty

## Technické detaily

### Modely
- `UserCoachAssignment`: Spojovací model mezi Coach a User
- Zachovává původní `CompanyProfile.assigned_coach` pro kompatibilitu
- Nový systém má přednost

### Oprávnění
- Funkce `can_coach_access_client()` nyní kontroluje přes UserCoachAssignment
- Coach vidí pouze své přiřazené klienty
- Admin interface filtruje ne-coach uživatele

### Views
- `my_clients`: Zobrazuje klienty z UserCoachAssignment
- `client_dashboard`: Ověřuje přístup přes UserCoachAssignment
- Zachována kompatibilita s existujícími templates

## Dotazy a odpovědi

**Q: Může jeden klient mít více koučů?**
A: Ne, model má `unique_together = ("coach", "client")` - jeden kouč na klienta.

**Q: Co když klient nemá CompanyProfile?**
A: Systém vytvoří dočasný objekt s username jako company_name.

**Q: Jak přidat více klientů najednou?**
A: V admin rozhraní u konkrétního kouče - sekce "User coach assignment" umožňuje přidat více řádků.

**Q: Kde vidím všechna přiřazení?**
A: Admin → Coaching → User coach assignments zobrazuje všechna přiřazení v systému.