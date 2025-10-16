# Interaktivní Coach Dashboard - Uživatelská příručka

## Přehled
Nový interaktivní dashboard umožňuje coachům efektivně přepínat mezi přiřazenými klienty a zobrazovat jejich data v real-time.

## Hlavní funkce

### 🎯 Sidebar s klienty
- **Levý panel** zobrazuje seznam všech přiřazených klientů
- **Kliknutím** na klienta se zobrazí jeho detailní dashboard
- **Barevné indikátory** ukazují počet nahraných výkazů
- **Aktivní klient** je zvýrazněn

### 📊 Interaktivní taby
Dashboard každého klienta obsahuje 4 hlavní sekce:

#### 1. **Přehled** 📊
- Základní statistiky klienta
- Nejnovější dokumenty
- Informace o firmě
- Dokončené dotazníky

#### 2. **Dokumenty** 📄
- Tabulka všech nahraných dokumentů
- Filtrování podle typu
- Přímé odkazy ke stažení
- Datum a velikost souborů

#### 3. **Cash Flow** 💰
- Analýza příjmů a výdajů
- Čistý cash flow
- Grafické zobrazení dat
- Roční přehledy

#### 4. **Poznámky** 📝
- Textové pole pro poznámky o klientovi
- Automatické ukládání
- Historie změn

## Jak používat

### Přihlášení a navigace
1. Přihlaste se jako coach (např. brona.klus@gmail.com)
2. V navigaci klikněte na "Coaching"
3. Otevře se interaktivní dashboard

### Práce s klienty
1. **Výběr klienta**: Klikněte na jméno klienta v levém panelu
2. **Zobrazení dat**: Data se načtou automaticky pomocí AJAX
3. **Přepínání tabů**: Klikněte na záložky pro různé sekce
4. **Ukládání poznámek**: Poznámky se ukládají automaticky

### AJAX funkcionalita
- **Real-time loading**: Data se načítají bez obnovení stránky
- **Loading indikátory**: Zobrazují se během načítání
- **Error handling**: Zobrazení chyb při problémech s načítáním

## Technické detaily

### URL struktura
```
/coaching/my-clients/                    - Hlavní dashboard
/coaching/client/{id}/data/             - AJAX: Základní data klienta
/coaching/client/{id}/documents-data/   - AJAX: Seznam dokumentů
/coaching/client/{id}/cashflow-data/    - AJAX: Cash flow analýza
/coaching/client/{id}/notes/            - POST: Ukládání poznámek
```

### JavaScript funkce
- `loadClientData()` - Načte základní data klienta
- `loadTabData()` - Načte data pro konkrétní tab
- `showLoading()` / `hideLoading()` - Správa loading indikátorů
- Auto-save poznámek s CSRF ochranou

## Výhody nového systému

### ✅ Pro uživatele
- **Rychlé přepínání** mezi klienty bez obnovení stránky
- **Přehledné rozhraní** s jasným rozdělením funkcí
- **Real-time data** - vždy aktuální informace
- **Intuitivní ovládání** - známé vzory UX

### ✅ Pro vývojáře
- **Modulární struktura** - snadné přidávání nových funkcí
- **AJAX endpoints** - rychlé a efektivní načítání dat
- **Error handling** - robustní zpracování chyb
- **Responsive design** - funguje na všech zařízeních

## Migrace ze starého systému

### Zachování kompatibility
- Starý dashboard je dostupný na `/coaching/my-clients-old/`
- Všechny existující URL zůstávají funkční
- Data se zobrazují stejně, jen s lepším UX

### Přechod pro uživatele
1. Existující uživatelé uvidí nové rozhraní automaticky
2. Všechna jejich data zůstávají zachována
3. Poznámky a přiřazení fungují stejně

## Řešení problémů

### Časté problémy
- **Prázdný seznam klientů**: Zkontrolujte přiřazení v Django admin
- **Nefungující AJAX**: Zkontrolujte CSRF token a síťové spojení
- **Chybějící data**: Ověřte oprávnění kouče ke klientovi

### Debug informace
- Django admin: `/admin/coaching/usercoachassignment/`
- Test přiřazení: `poetry run python test_coach_assignment.py`
- Log serveru: Sledujte výstup `manage.py runserver`

## Budoucí rozšíření

### Plánované funkce
- 📈 **Grafické grafy** - vizualizace cash flow
- 🔔 **Notifikace** - upozornění na nové dokumenty
- 📱 **Mobile app** - React Native aplikace
- 💬 **Chat systém** - komunikace s klienty

### Možná vylepšení
- Filtrování a vyhledávání klientů
- Exporty dat do PDF/Excel
- Kalendář a schůzky
- Bulk operace s dokumenty

---

## 🎉 ROZŠÍŘENÝ DASHBOARD - NOVÉ FUNKCE V2.0

### ✅ Přidané sekce:

#### **📈 Grafy (Chart.js)**
- **Finanční výkonnost** - doughnut chart (příjmy/výdaje/investice)
- **Trend příjmů/výdajů** - line chart s 6měsíčními daty  
- **Aktivita podle měsíců** - bar chart (dokumenty + dotazníky)
- **Plně interaktivní a responsive grafy**

#### **📋 Dotazníky (Survey)**
- **Accordion rozbalovací design** pro Q&A
- **Progress bary pro skóre 1-10** - vizuální hodnocení
- **AI analýzy** - inteligentní insights pro každý batch
- **Batch seskupování** podle submission ID

#### **🔓 Suropen odpovědi**
- **3 barevné sekce**: VÍCE ČASU (modrá) / VÍCE PENĚZ (zelená) / MÉNĚ STRACHU (žlutá)
- **Batch timeline** - chronologické řazení sezení
- **Q&A preview** s zkrácenými náhledy
- **AI insights** centralizované pro každý batch

### 🎯 Testovací data vytvořena:
- ✅ **6 survey submissions** s 30 strukturovanými odpověďmi
- ✅ **4 suropen batche** s 36 odpověďmi ve 3 sekcích
- ✅ **AI analýzy** pro všechny batche s realistickým obsahem
- ✅ **Oba test klienti** (test_client, client@example.com) mají kompletní data

### 🚀 Finální výsledek:
**Kompletní 360° business intelligence dashboard s AI-powered insights, vizuálními grafy a strukturovanými daty pro efektivní koučování!**

### 📱 Jak otestovat:
1. Otevřete http://127.0.0.1:8000/coaching/my-clients/
2. Klikněte na "test_client" v levém panelu
3. Projděte všech 6 tabů: Přehled → Dokumenty → Cash Flow → **Grafy** → **Dotazníky** → **Suropen** → Poznámky
4. Vyzkoušejte interaktivní grafy a rozbalovací accordion