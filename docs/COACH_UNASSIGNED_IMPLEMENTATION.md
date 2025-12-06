# Implementace "Nepřiřazení uživatelé" pro Coach Dashboard

## Datum implementace: 2025-12-06
## Branch: coachmodule
## Commity: 61b43d4, 7a41791

---

## Přehled implementované funkcionality

Kouči nyní mohou:
1. ✅ **Vidět všechny nepřiřazené uživatele** v systému (společný pool pro všechny kouče)
2. ✅ **Přiřadit si klienty k sobě** jedním kliknutím
3. ✅ **Vidět badge s počtem nepřiřazených** přímo v dashboardu
4. ✅ **Kouči se nezobrazují** jako nepřiřazení (filtrováno podle role)

---

## Implementované soubory

### 1. Nové soubory

#### `templates/coaching/unassigned_users.html` (257 řádků)
- Moderní tabulka s nepřiřazenými uživateli
- Statistiky: Firma, IČO, Email, Dny od registrace, Počet dokumentů, Stav onboardingu
- AJAX přiřazení s live update
- Toast notifikace o úspěchu

### 2. Upravené soubory

#### `coaching/views.py`
**Přidáno:**
- `unassigned_users()` view (řádky 404-447)
- `assign_client_to_self()` view (řádky 450-496)
- Filtrování koučů v `my_clients()` (řádky 90-100)

**Klíčová logika:**
```python
# Filtrování koučů ze seznamu nepřiřazených
from accounts.models import UserRole
coach_user_ids = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)

unassigned = CompanyProfile.objects.filter(
    assigned_coach__isnull=True  # Legacy system
).exclude(
    user__usercoachassignment__isnull=False  # New system
).exclude(
    user_id__in=coach_user_ids  # Vyfiltruj kouče
).select_related('user').order_by('-created_at')
```

#### `coaching/urls.py`
**Přidáno:**
- `path("unassigned-users/", views.unassigned_users, name="unassigned_users")`
- `path("assign-client/<int:client_id>/", views.assign_client_to_self, name="assign_client")`
- Redirect `path("", RedirectView.as_view(pattern_name="coaching:my_clients"), name="coaching_home")`

#### `coaching/templates/coaching/modern_dashboard.html`
**Přidáno tlačítko v headeru:**
```html
{% if unassigned_count > 0 %}
<a href="{% url 'coaching:unassigned_users' %}"
   class="inline-flex items-center gap-2 rounded-full bg-amber-500 text-white px-4 py-2 text-sm font-semibold shadow-sm hover:bg-amber-600 transition">
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
  </svg>
  Nepřiřazení ({{ unassigned_count }})
</a>
{% endif %}
```

---

## Jak to funguje

### Flow 1: Registrace bez kouče

```
1. Uživatel vyplní registrační formulář
   └─ http://127.0.0.1:8000/accounts/register/

2. Dropdown "Přiřazený kouč" - vybere "-- bez kouče --"

3. Uživatel je vytvořen v DB
   ├─ CompanyProfile.assigned_coach = NULL
   └─ UserRole.role = 'company'

4. Uživatel není vidět v žádném coach dashboardu
```

### Flow 2: Kouč vidí nepřiřazené

```
1. Kouč se přihlásí
   └─ http://127.0.0.1:8000/accounts/login/

2. Redirect na /coaching/my-clients/

3. my_clients() view počítá nepřiřazené
   ├─ Filtruje: assigned_coach__isnull=True
   ├─ Exclude: user__usercoachassignment__isnull=False
   └─ Exclude: user_id__in=coach_user_ids  # KLÍČOVÉ!

4. Badge "Nepřiřazení (X)" se zobrazí v headeru
   └─ Pouze pokud unassigned_count > 0
```

### Flow 3: Kouč přiřadí klienta

```
1. Kouč klikne na tlačítko "Nepřiřazení (X)"
   └─ GET /coaching/unassigned-users/

2. unassigned_users() view načte seznam
   ├─ Stejná filtrace jako v my_clients()
   └─ Přidá statistiky (docs_count, days_since_registration, onboarding)

3. Tabulka zobrazí nepřiřazené uživatele

4. Kouč klikne "Přiřadit" u konkrétního klienta
   ├─ JavaScript: AJAX POST request
   └─ POST /coaching/assign-client/<client_id>/

5. assign_client_to_self() view zpracuje
   ├─ Ověří, že klient nemá kouče
   ├─ Vytvoří UserCoachAssignment (nový systém)
   ├─ Nastaví CompanyProfile.assigned_coach (legacy)
   └─ Vrátí JSON: {"success": true, "client_name": "..."}

6. JavaScript odstraní řádek z tabulky
   └─ Live update bez reload

7. Badge se aktualizuje po reload
```

---

## Klíčové vlastnosti

### ✅ Globální pool nepřiřazených

**Všichni kouči vidí stejný seznam:**
- Není to filtrované podle konkrétního kouče
- Každý kouč vidí všechny nepřiřazené uživatele
- First-come-first-served princip

**Výhody:**
- Žádný uživatel nezůstane opomenut
- Každý kouč si může vybrat klienty
- Flexibilní distribuce zatížení

### ✅ Filtrování koučů

**Problém:**
Původně se kouči zobrazovali jako nepřiřazení uživatelé (protože sami nemají přiřazeného kouče).

**Řešení:**
```python
# Získej ID všech koučů
coach_user_ids = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)

# Vyfiltruj je z nepřiřazených
.exclude(user_id__in=coach_user_ids)
```

**Použito v:**
1. `my_clients()` - počítání badge
2. `unassigned_users()` - zobrazení seznamu

### ✅ Duální systém přiřazování

**Při přiřazení se zapisuje do obou systémů:**

```python
# Nový systém (preferovaný)
UserCoachAssignment.objects.create(
    coach=coach,
    client=client_profile.user,
    notes='Kouč si přiřadil klienta sám'
)

# Legacy systém (backward compatibility)
client_profile.assigned_coach = coach
client_profile.save(update_fields=['assigned_coach'])
```

**Důvod:**
- Zajištění kompatibility se starou logikou
- Postupná migrace na nový systém
- Žádné breaking changes

### ✅ Bezpečnost

**Implementované kontroly:**

1. **Autentizace:** `@login_required`
2. **Autorizace:** `@coach_required`
3. **HTTP metoda:** POST only pro přiřazení
4. **CSRF token:** Automaticky přes Django
5. **Validace stavu:** Kontrola, že klient nemá kouče
6. **Exception handling:** Try-catch s JSON error response

---

## URL Routing

### Nové endpointy

| URL | View | Metoda | Popis |
|-----|------|--------|-------|
| `/coaching/` | RedirectView | GET | Redirect na my-clients |
| `/coaching/unassigned-users/` | `unassigned_users` | GET | Seznam nepřiřazených |
| `/coaching/assign-client/<id>/` | `assign_client_to_self` | POST | Přiřazení klienta |

### Existující endpointy (nezměněno)

| URL | View | Popis |
|-----|------|-------|
| `/coaching/my-clients/` | `my_clients` | Coach dashboard (+ badge) |
| `/coaching/client/<id>/` | `client_dashboard` | Dashboard konkrétního klienta |
| `/coaching/edit/` | `edit_coach` | Úprava profilu kouče |

---

## Databázové queries

### Query pro nepřiřazené (optimalizované)

```python
from accounts.models import UserRole, CompanyProfile
from coaching.models import UserCoachAssignment

# 1. Získej ID všech koučů (1 query)
coach_user_ids = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)

# 2. Najdi nepřiřazené (1 query s JOIN)
unassigned = CompanyProfile.objects.filter(
    assigned_coach__isnull=True
).exclude(
    user__usercoachassignment__isnull=False
).exclude(
    user_id__in=coach_user_ids
).select_related('user')  # Optimalizace: Předčítání user

# Celkem: 2 queries
```

**Optimalizace:**
- `select_related('user')` - Předčítá user objekt (JOIN místo N+1 queries)
- `values_list('user_id', flat=True)` - Vrací jen ID, ne celé objekty
- `.count()` vs `len()` - Pro badge používáme `.count()` (DB-level)

### Query pro statistiky (v unassigned_users view)

```python
for profile in unassigned:
    # Pro každý profil: 1 query
    docs_count = Document.objects.filter(owner=profile.user).count()
    # ...
```

**Možná optimalizace (budoucí):**
```python
# Prefetch všechny dokumenty najednou
from django.db.models import Count
unassigned = unassigned.annotate(
    docs_count=Count('user__document')
)
```

---

## Testování

### Manuální test

**1. Vytvoř testovacího uživatele bez kouče:**

```bash
python manage.py shell

from django.contrib.auth.models import User
from accounts.models import CompanyProfile, UserRole

user = User.objects.create_user(
    username='testfirma@example.com',
    email='testfirma@example.com',
    password='testpass123'
)

UserRole.objects.create(user=user, role='company')

CompanyProfile.objects.create(
    user=user,
    company_name='Test Firma s.r.o.',
    ico='12345678',
    contact_person='Jan Novák',
    phone='+420123456789',
    # assigned_coach není nastaven!
)

print(f'Created: {user.email}')
exit()
```

**2. Přihlaš se jako kouč:**
- URL: http://127.0.0.1:8000/accounts/login/
- Použij credentials kouče

**3. Zkontroluj badge:**
- Mělo by se zobrazit: "Nepřiřazení (1)"
- Pokud ne → pravděpodobně je kouč sám v seznamu (chyba filtrace)

**4. Klikni na badge:**
- Měla by se zobrazit tabulka
- Test Firma s.r.o. by měla být v seznamu

**5. Přiřaď klienta:**
- Klikni "Přiřadit"
- Potvrdí dialog
- Řádek zmizí
- Toast: "Klient Test Firma s.r.o. byl úspěšně přiřazen."

**6. Ověř přiřazení:**
- Vrať se na /coaching/my-clients/
- Test Firma by měla být v "Moji klienti"
- Badge "Nepřiřazení" by měl zmizet (nebo ukazovat 0)

### Unit test (budoucí)

```python
# tests/test_unassigned_users.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from accounts.models import UserRole, CompanyProfile
from coaching.models import Coach

class UnassignedUsersTest(TestCase):
    def setUp(self):
        # Create coach
        self.coach_user = User.objects.create_user('coach@test.com', password='test')
        UserRole.objects.create(user=self.coach_user, role='coach')
        self.coach = Coach.objects.create(user=self.coach_user)

        # Create unassigned company
        self.company_user = User.objects.create_user('company@test.com', password='test')
        UserRole.objects.create(user=self.company_user, role='company')
        self.company_profile = CompanyProfile.objects.create(
            user=self.company_user,
            company_name='Test Company'
        )

        self.client = Client()

    def test_coach_sees_unassigned(self):
        """Test that coach can see unassigned users"""
        self.client.login(username='coach@test.com', password='test')
        response = self.client.get('/coaching/unassigned-users/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Company')

    def test_coach_not_in_unassigned(self):
        """Test that coaches themselves are not shown as unassigned"""
        self.client.login(username='coach@test.com', password='test')
        response = self.client.get('/coaching/unassigned-users/')

        # Coach should NOT see themselves
        self.assertNotContains(response, self.coach_user.email)

    def test_assign_client(self):
        """Test that coach can assign client to themselves"""
        self.client.login(username='coach@test.com', password='test')
        response = self.client.post(
            f'/coaching/assign-client/{self.company_profile.id}/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # Verify assignment in both systems
        self.company_profile.refresh_from_db()
        self.assertEqual(self.company_profile.assigned_coach, self.coach)
```

---

## Monitoring & Metriky

### Metriky k sledování

```python
from accounts.models import CompanyProfile, UserRole
from coaching.models import UserCoachAssignment
from django.utils import timezone
from datetime import timedelta

# 1. Počet nepřiřazených (měl by klesat)
coach_ids = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)
unassigned_count = CompanyProfile.objects.filter(
    assigned_coach__isnull=True
).exclude(
    user__usercoachassignment__isnull=False
).exclude(
    user_id__in=coach_ids
).count()

# 2. Průměrná doba do přiřazení
from django.db.models import Avg, F, ExpressionWrapper, fields
avg_time = UserCoachAssignment.objects.annotate(
    time_to_assign=ExpressionWrapper(
        F('assigned_at') - F('client__date_joined'),
        output_field=fields.DurationField()
    )
).aggregate(avg=Avg('time_to_assign'))

# 3. Self-assignments za poslední týden
self_assigned = UserCoachAssignment.objects.filter(
    notes__icontains='Kouč si přiřadil klienta sám',
    assigned_at__gte=timezone.now() - timedelta(days=7)
).count()

# 4. Rozdělení klientů mezi kouče
from django.db.models import Count
coach_distribution = Coach.objects.annotate(
    client_count=Count('usercoachassignment')
).values('user__email', 'client_count').order_by('-client_count')

print(f'Nepřiřazeno: {unassigned_count}')
print(f'Průměrná doba do přiřazení: {avg_time["avg"]}')
print(f'Self-assignments (7d): {self_assigned}')
print(f'Rozdělení klientů:')
for coach in coach_distribution:
    print(f'  {coach["user__email"]}: {coach["client_count"]} klientů')
```

---

## Troubleshooting

### Problém 1: Badge neukazuje správný počet

**Symptom:** Tlačítko "Nepřiřazení (X)" neukazuje očekávaný počet.

**Možné příčiny:**
1. Kouči se počítají jako nepřiřazení
2. Cache problém

**Řešení:**
```python
# Zkontroluj v shell
from accounts.models import UserRole, CompanyProfile

coach_ids = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)
print(f'Coach IDs: {list(coach_ids)}')

unassigned = CompanyProfile.objects.filter(
    assigned_coach__isnull=True
).exclude(
    user__usercoachassignment__isnull=False
).exclude(
    user_id__in=coach_ids
)
print(f'Unassigned count: {unassigned.count()}')
print(f'Unassigned users: {[p.company_name for p in unassigned]}')
```

### Problém 2: Kouč vidí sám sebe v seznamu

**Symptom:** Kouč se zobrazuje jako nepřiřazený uživatel.

**Příčina:** Chybí filtrování podle UserRole.

**Řešení:** Ověř, že v `unassigned_users()` view je:
```python
coach_user_ids = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)
.exclude(user_id__in=coach_user_ids)
```

### Problém 3: "Tento klient již má přiřazeného kouče"

**Symptom:** Nelze přiřadit klienta, i když by to mělo jít.

**Možné příčiny:**
1. Race condition - jiný kouč přiřadil klienta mezitím
2. Data inconsistency - má přiřazení v jednom systému, ale ne druhém

**Řešení:**
```python
# Zkontroluj v shell
from accounts.models import CompanyProfile
from coaching.models import UserCoachAssignment

profile = CompanyProfile.objects.get(id=CLIENT_ID)
print(f'Legacy coach: {profile.assigned_coach}')

assignments = UserCoachAssignment.objects.filter(client=profile.user)
print(f'New system assignments: {assignments.count()}')
for a in assignments:
    print(f'  Coach: {a.coach}, Date: {a.assigned_at}')
```

---

## Budoucí vylepšení

### v2.0 Features

- [ ] **Email notifikace** - Pošli email koučovi při nové registraci
- [ ] **Auto-assignment** - Automaticky přiřaď podle oboru/města
- [ ] **Bulk assignment** - Přiřaď více klientů najednou
- [ ] **Coach capacity** - Limit klientů na kouče
- [ ] **Assignment history** - Audit log všech přiřazení
- [ ] **Smart recommendations** - AI doporučení koučů

### Performance optimalizace

- [ ] Caching badge počtu (Redis)
- [ ] Prefetch dokumentů v unassigned_users view
- [ ] Denní email digest pro kouče

---

## Závěr

✅ **Implementováno:**
- Globální pool nepřiřazených uživatelů
- Self-assignment pro kouče
- Badge v dashboardu
- Filtrování koučů ze seznamu

✅ **Commity:**
- `61b43d4` - Add unassigned users management for coaches
- `7a41791` - Filter coaches from unassigned users list

✅ **Dokumentace:**
- Tento soubor
- COACH_SYSTEM_PROPOSAL.md (detailní návrh)
- COACH_UNASSIGNED_USERS_INTEGRATION.md (návod na integraci)

**Poznámka:** Všechny změny jsou na branch `coachmodule`.
