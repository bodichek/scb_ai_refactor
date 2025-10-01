import os
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Document, FinancialStatement
from .openai_parser import analyze_income, analyze_balance
from django.http import HttpResponse




@login_required
def documents_list(request):
    """Seznam všech dokumentů uživatele."""
    docs = Document.objects.filter(owner=request.user).order_by("-uploaded_at")
    return render(request, "ingest/documents_list.html", {"documents": docs})


@login_required
def upload_pdf(request):
    if request.method == "POST" and request.FILES.get("pdf_file"):
        file = request.FILES["pdf_file"]
        year = request.POST.get("year") or 2025  # TODO: doplnit formulář na rok
        doc_type = request.POST.get("doc_type") or "income"  # income / balance

        # uložíme originální dokument
        doc = Document.objects.create(owner=request.user, file=file, year=year, doc_type=doc_type)

        # cesta k uloženému souboru
        pdf_path = doc.file.path

        # pošleme do OpenAI podle typu
        if doc_type == "income":
            data = analyze_income(pdf_path)
        else:
            data = analyze_balance(pdf_path)

        # uložíme výsledek
        FinancialStatement.objects.create(
            owner=request.user,
            document=doc,
            year=year,
            data=data
        )

        return redirect("dashboard:index")

    return render(request, "ingest/upload.html")


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