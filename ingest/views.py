from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Document, FinancialStatement
from .openai_parser import analyze_income, analyze_balance


@login_required
def documents_list(request):
    """Seznam všech dokumentů uživatele."""
    docs = Document.objects.filter(owner=request.user).order_by("-uploaded_at")
    return render(request, "ingest/documents_list.html", {"documents": docs})


@login_required
def upload_pdf(request):
    """
    Upload PDF souboru – uživatel vybere rok a typ výkazu (income/balance).
    """
    if request.method == "POST" and request.FILES.get("file"):
        year = int(request.POST.get("year") or 0) or 2024
        doc_type = request.POST.get("doc_type") or "income"

        doc = Document.objects.create(
            owner=request.user,
            file=request.FILES["file"],
            year=year,
        )
        # musíme mít v Document modelu pole doc_type = models.CharField(...)
        doc.doc_type = doc_type
        doc.save()

        return redirect("process_pdf", document_id=doc.id)

    return render(request, "ingest/upload.html")


@login_required
def process_pdf(request, document_id: int):
    """
    Zpracuje PDF → zavolá správný OpenAI parser → uloží metriky do DB.
    """
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    pdf_path = document.file.path

    # Rozhodnutí podle typu výkazu
    if getattr(document, "doc_type", "income") == "income":
        data = analyze_income(pdf_path)
    else:
        data = analyze_balance(pdf_path)

    FinancialStatement.objects.update_or_create(
        owner=request.user,
        year=document.year,
        defaults={"document": document, "data": data},
    )

    return redirect("dashboard")
