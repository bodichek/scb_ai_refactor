SCB Frontend (React + Vite + Tailwind)

Rychlý start
- Požadavky: Node.js 18+, npm nebo yarn/pnpm
- Instalace: `npm install` v adresáři `frontend`
- Vývoj: `npm run dev` (http://localhost:5173)
- Build: `npm run build` (výstup v `frontend/dist`)

Propojení s backendem
- Dev proxy je nastavená ve `vite.config.ts` pro cesty: `/accounts`, `/coaching`, `/dashboard`, `/ingest`, `/survey`, `/suropen`, `/exports`, `/chatbot`, `/api` → `http://localhost:8000`.
- Není nutné nastavovat `VITE_API_BASE_URL` v dev režimu. Pro produkci použijte `.env`.

Integrace s Django
- Dev proxy: doporučeno nastavit Nginx/traefik nebo Vite proxy pro předávání na Django (`localhost:8000`).
- Produkce: zvažte nasazení statiky z `frontend/dist` pod Django `STATICFILES_DIRS` nebo reverzní proxy.

Struktura
- `src/components` – Navbar, Tile komponenty
- `src/tiles` – Dlaždice: Grafy, Analýza, Dotazník, Nahrání souboru
- `src/lib/api.ts` – jednoduchý klient pro volání API (cookie-based session podporováno)

Poznámky
- Autentizace v Navbaru je zatím mock. Lze doplnit přihlášení přes `accounts/login/` (form POST, CSRF) nebo vlastní JSON endpoint.
- Dlaždice už volají reálné endpointy:
  - Grafy: `GET /dashboard/api/cashflow/<year>/` (vrací HTML v JSON → renderováno v dlaždici)
  - Analýza/poznámky: `POST /coaching/client/<id>/notes/` (form-data `notes`)
  - Nahrání souboru: `POST /ingest/upload/` (form-data `pdf_file`, `year`)
  - Chatbot (k dispozici, zatím není v UI): `POST /chatbot/api/` (JSON `{message, context}`)
- CSRF: pro POSTy posíláme `X-CSRFToken` z cookie `csrftoken` (Django výchozí). Pro `chatbot/api` a `accounts/api/company-data/` není CSRF potřeba.
- Barvy: v `tailwind.config.js` je paleta `brand`/`primary` připravená k výměně za barvy ScaleupBoard.
