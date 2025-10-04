import os
import json
from django.db.models import Max
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from .models import Document, FinancialStatement
from .openai_parser import (
    analyze_income,
    analyze_balance,
    detect_doc_type,
    detect_doc_type_and_year,
)


from django.db.models import Max

@login_required
def documents_list(request):
    """
    Seznam dokumentů s přepínačem režimu:
    - Jen aktuální (nejnovější rozvaha a výkaz za rok)
    - Všechny nahrané soubory
    """
    show_all = request.GET.get("vse") == "1"  # ?vse=1 → zobrazí všechny

    if show_all:
        # zobrazíme všechny nahrané dokumenty
        docs = (
            Document.objects
            .filter(owner=request.user)
            .order_by("-year", "-uploaded_at")
        )
    else:
        # zobrazíme jen nejnovější dokumenty (1 rozvaha + 1 výkaz za rok)
        latest_docs = (
            Document.objects
            .filter(owner=request.user)
            .values("year", "doc_type")
            .annotate(last_id=Max("id"))
            .values_list("last_id", flat=True)
        )
        docs = (
            Document.objects
            .filter(id__in=latest_docs)
            .order_by("-year", "doc_type")
        )

    # doplníme info o datu aktualizace z FinancialStatement
    for d in docs:
        fs = FinancialStatement.objects.filter(document=d).first()
        d.last_updated = getattr(fs, "created_at", None)

    return render(request, "ingest/documents_list.html", {
        "documents": docs,
        "show_all": show_all,
    })


@login_required
def upload_pdf(request):
    """Jednoduché nahrání jednoho PDF (původní funkce)."""
    if request.method == "POST" and request.FILES.get("pdf_file"):
        file = request.FILES["pdf_file"]
        year = int(request.POST.get("year") or 2025)

        doc = Document.objects.create(owner=request.user, file=file, year=year)
        pdf_path = doc.file.path

        # Detekce typu pomocí OpenAI
        doc_type = detect_doc_type(pdf_path)
        doc.doc_type = doc_type

        # Spustíme analýzu
        if doc_type == "income":
            new_data = analyze_income(pdf_path)
        else:
            new_data = analyze_balance(pdf_path)

        doc.analyzed = True
        doc.save(update_fields=["doc_type", "analyzed"])

        # Uložení do FinancialStatement
        with transaction.atomic():
            fs, created = FinancialStatement.objects.get_or_create(
                owner=request.user,
                year=doc.year,
                defaults={"document": doc, "data": new_data},
            )
            if not created:
                fs.document = doc
                fs.data = new_data
                fs.save()
                print(f"[UPDATE] Rok {doc.year}: stará data přepsána novými")
            else:
                print(f"[CREATE] Rok {doc.year}: vytvořen nový záznam")

        return redirect("dashboard:index")

    years = list(range(2020, 2026))
    return render(request, "ingest/upload.html", {"years": years})


@login_required
def upload_many(request):
    """
    📁 Multiupload – umožní nahrát více PDF souborů najednou.
    OpenAI automaticky určí typ i rok a spustí analýzu.
    """
    if request.method == "POST":
        files = request.FILES.getlist("pdf_files")
        results = []

        for f in files:
            try:
                # 1️⃣ Vytvoříme záznam s dočasným rokem (aby nevznikla DB chyba)
                doc = Document.objects.create(owner=request.user, file=f, year=2025)
                pdf_path = doc.file.path

                # 2️⃣ OpenAI rozpozná typ a rok
                from .openai_parser import detect_doc_type_and_year
                meta = detect_doc_type_and_year(pdf_path)

                doc.doc_type = meta.get("type", "income")
                doc.year = meta.get("year", 2025)
                doc.save(update_fields=["doc_type", "year"])

                # 3️⃣ Analýza podle typu
                if doc.doc_type == "income":
                    data = analyze_income(pdf_path)
                else:
                    data = analyze_balance(pdf_path)

                doc.analyzed = True
                doc.save(update_fields=["analyzed"])

                # 4️⃣ Uložení výsledků do FinancialStatement
                with transaction.atomic():
                    fs, created = FinancialStatement.objects.get_or_create(
                        owner=request.user,
                        year=doc.year,
                        defaults={"document": doc, "data": data},
                    )
                    if not created:
                        merged = fs.data or {}
                        merged.update(data)
                        fs.document = doc
                        fs.data = merged
                        fs.save()

                # 5️⃣ Výsledek pro přehled
                results.append({
                    "file": f.name,
                    "year": doc.year,
                    "type": doc.get_doc_type_display(),
                    "status": "✅ Analyzováno"
                })

                print(f"[OK] {f.name} → {doc.doc_type}, rok {doc.year}")

            except Exception as e:
                print(f"[CHYBA] {f.name}: {e}")
                results.append({
                    "file": f.name,
                    "year": "-",
                    "type": "-",
                    "status": f"❌ Chyba: {e}"
                })

        return render(request, "ingest/upload_many_result.html", {"results": results})

    return render(request, "ingest/upload_many.html")


@login_required
def process_pdf(request, document_id: int):
    """Ruční spuštění analýzy (fallback)."""
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    pdf_path = document.file.path

    if document.doc_type == "income":
        data = analyze_income(pdf_path)
    else:
        data = analyze_balance(pdf_path)

    FinancialStatement.objects.update_or_create(
        owner=request.user,
        year=document.year,
        defaults={"document": document, "data": data},
    )

    return redirect("dashboard:index")


@login_required
def delete_document(request, document_id: int):
    """Smazání dokumentu + napojených dat."""
    doc = get_object_or_404(Document, id=document_id, owner=request.user)
    if os.path.exists(doc.file.path):
        os.remove(doc.file.path)
    doc.delete()
    messages.success(request, "📄 Dokument byl úspěšně smazán.")
    return redirect("ingest:documents")
