import os
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Document, FinancialStatement
from .openai_parser import analyze_income, analyze_balance, detect_doc_type
from django.http import HttpResponse
from django.db import transaction




@login_required
def documents_list(request):
    """Seznam všech dokumentů uživatele (spíš kontrolní)."""
    docs = Document.objects.filter(owner=request.user).order_by("-uploaded_at")
    return render(request, "ingest/documents_list.html", {"documents": docs})


@login_required
def upload_pdf(request):
    if request.method == "POST" and request.FILES.get("pdf_file"):
        file = request.FILES["pdf_file"]
        year = int(request.POST.get("year") or 2025)

        # uložíme dokument
        doc = Document.objects.create(owner=request.user, file=file, year=year)

        pdf_path = doc.file.path

        # AI detekce typu
        doc_type = detect_doc_type(pdf_path)
        doc.doc_type = doc_type

        # spustíme analýzu
        if doc_type == "income":
            new_data = analyze_income(pdf_path)
        else:
            new_data = analyze_balance(pdf_path)

        doc.analyzed = True
        doc.save(update_fields=["doc_type", "analyzed"])

        # ✅ merge dat do jednoho řádku FinancialStatement
        with transaction.atomic():
            fs, created = FinancialStatement.objects.get_or_create(
                owner=request.user,
                year=year,
                defaults={"document": doc, "data": new_data},
            )
            if not created:
                # spojíme nová a stará data
                merged_data = fs.data or {}
                merged_data.update(new_data)
                fs.document = doc
                fs.data = merged_data
                fs.save()

        return redirect("dashboard:index")

    years = list(range(2020, 2026))
    return render(request, "ingest/upload.html", {"years": years})

    # nabídka let
    years = list(range(2020, 2026))
    return render(request, "ingest/upload.html", {"years": years})



@login_required
def process_pdf(request, document_id: int):
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    pdf_path = document.file.path

    if document.doc_type == "income":
        data = analyze_income(pdf_path)
    else:
        data = analyze_balance(pdf_path)

    print(">>> Saving FS:", document.year, request.user, data)  # ⬅️ Debug výpis

    FinancialStatement.objects.update_or_create(
        owner=request.user,
        year=document.year,
        defaults={"document": document, "data": data},
    )

    return redirect("dashboard:index")

@login_required
def delete_document(request, document_id: int):
    """Smazání dokumentu + všech napojených dat."""
    doc = get_object_or_404(Document, id=document_id, owner=request.user)

    # smažeme fyzický soubor ze storage
    file_path = doc.file.path
    if os.path.exists(file_path):
        os.remove(file_path)

    # smažeme záznam v DB (smaže i FinancialStatement díky CASCADE)
    doc.delete()

    messages.success(request, "📄 Dokument byl úspěšně smazán.")
    return redirect("ingest:documents")