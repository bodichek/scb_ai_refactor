import os
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import Document, FinancialStatement
from .ai_parser_refactored import (
    analyze_income,
    analyze_balance,
    detect_doc_type,
    detect_doc_type_and_year,
    calculate_metrics,
)

INCOME_FIELDS = [
    "revenue_products_services",
    "revenue_goods",
    "cogs_goods",
    "cogs_materials",
    "services",
    "personnel_wages",
    "personnel_insurance",
    "taxes_fees",
    "depreciation",
    "other_operating_costs",
    "other_operating_revenue",
    "financial_revenue",
    "financial_costs",
    "income_tax",
]

BALANCE_FIELDS = [
    "receivables",
    "inventory",
    "short_term_liabilities",
    "cash",
]


def _persist_statement(doc, parsed_data):
    with transaction.atomic():
        fs, created = FinancialStatement.objects.get_or_create(
            owner=doc.owner,
            year=doc.year,
            defaults={"document": doc, "data": {}},
        )
        existing = fs.data or {}
        payload = dict(existing)

        if doc.doc_type == "income":
            balance_for_metrics = {
                key: existing.get(key) for key in BALANCE_FIELDS if existing.get(key) is not None
            }
            balance_for_metrics = balance_for_metrics if any(balance_for_metrics.values()) else None
            metrics = calculate_metrics(parsed_data, balance_for_metrics)
            payload.update({k: v for k, v in metrics.items() if k != "overheads"})
        else:
            payload.update(parsed_data)
            income_available = any(key in existing for key in INCOME_FIELDS)
            if income_available:
                income_data = {k: existing.get(k, 0) for k in INCOME_FIELDS}
                balance_for_metrics = {k: payload.get(k, 0) for k in BALANCE_FIELDS}
                metrics = calculate_metrics(income_data, balance_for_metrics)
                payload.update({k: v for k, v in metrics.items() if k != "overheads"})

        # Never persist stored overhead totals; compute from components on read
        for legacy_key in ("Overheads", "overheads"):
            payload.pop(legacy_key, None)

        fs.document = doc
        fs.data = payload
        fs.save()

    return fs



def _process_uploaded_file(user, uploaded_file):
    """Process one PDF file and store parsed results."""
    # Dočasně nastavíme rok, aby se dokument uložil
    doc = Document.objects.create(owner=user, file=uploaded_file, year=2025)
    pdf_path = doc.file.path

    meta = detect_doc_type_and_year(pdf_path)
    doc.doc_type = meta.get("type", "income")
    doc.year = meta.get("year", 2025)
    doc.save(update_fields=["doc_type", "year"])

    if doc.doc_type == "income":
        parsed_data = analyze_income(pdf_path)
    else:
        parsed_data = analyze_balance(pdf_path)

    doc.analyzed = True
    doc.save(update_fields=["analyzed"])

    _persist_statement(doc, parsed_data)

    return {
        "file": uploaded_file.name,
        "year": doc.year,
        "type": doc.get_doc_type_display() if hasattr(doc, "get_doc_type_display") else doc.doc_type,
        "status": "Analyzováno",
        "success": True,
        "document": _serialize_document(doc),
    }



def _serialize_document(doc: Document):
    statement = FinancialStatement.objects.filter(document=doc).first()
    return {
        "id": doc.id,
        "filename": doc.filename or os.path.basename(doc.file.name),
        "year": doc.year,
        "doc_type": doc.doc_type,
        "doc_type_display": doc.get_doc_type_display() if hasattr(doc, "get_doc_type_display") else doc.doc_type,
        "analyzed": doc.analyzed,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "last_updated": statement.created_at.isoformat() if statement else None,
        "url": doc.file.url if doc.file else "",
    }


@login_required
def documents_list(request):
    """Původní HTML seznam dokumentů (pro kompatibilitu)."""
    show_all = request.GET.get("vse") == "1"

    if show_all:
        docs = Document.objects.filter(owner=request.user).order_by("-year", "-uploaded_at")
    else:
        latest_ids = (
            Document.objects
            .filter(owner=request.user)
            .values("year", "doc_type")
            .annotate(last_id=Max("id"))
            .values_list("last_id", flat=True)
        )
        docs = Document.objects.filter(id__in=latest_ids).order_by("-year", "doc_type")

    for doc in docs:
        statement = FinancialStatement.objects.filter(document=doc).first()
        doc.last_updated = getattr(statement, "created_at", None)

    return render(request, "ingest/documents_list.html", {"documents": docs, "show_all": show_all})


@login_required
def upload_pdf(request):
    """Jednoduchý upload jednoho PDF – historický pohled."""
    if request.method == "POST" and request.FILES.get("pdf_file"):
        file = request.FILES["pdf_file"]
        year = int(request.POST.get("year") or 2025)

        doc = Document.objects.create(owner=request.user, file=file, year=year)
        pdf_path = doc.file.path

        doc_type = detect_doc_type(pdf_path)
        doc.doc_type = doc_type

        if doc_type == "income":
            new_data = analyze_income(pdf_path)
        else:
            new_data = analyze_balance(pdf_path)

        doc.analyzed = True
        doc.save(update_fields=["doc_type", "analyzed"])

        _persist_statement(doc, new_data)

        return redirect("dashboard:index")

    years = list(range(2020, 2026))
    return render(request, "ingest/upload.html", {"years": years})


@login_required
def upload_many(request):
    """HTML stránka pro multiupload – kompatibilita."""
    if request.method == "POST":
        files = request.FILES.getlist("pdf_files")
        results = []

        for f in files:
            try:
                result = _process_uploaded_file(request.user, f)
                results.append(result)
                print(f"[OK] {f.name} -> {result['type']}, rok {result['year']}")
            except Exception as exc:  # pragma: no cover - log only
                print(f"[CHYBA] {f.name}: {exc}")
                results.append({
                    "file": f.name,
                    "year": "-",
                    "type": "-",
                    "status": f"Chyba: {exc}",
                    "success": False,
                })

        return render(request, "ingest/upload_many_result.html", {"results": results})

    return render(request, "ingest/upload_many.html")


@login_required
@require_http_methods(["GET", "POST"])
def documents_api(request):
    """
    JSON API pro dokumenty.
    GET ?scope=all|latest – seznam dokumentů.
    POST – nahrání jednoho nebo více souborů (pole `pdf_files` v multipart form-data).
    """
    if request.method == "GET":
        scope = request.GET.get("scope", "latest")
        docs_qs = Document.objects.filter(owner=request.user)
        if scope == "all":
            docs = docs_qs.order_by("-year", "-uploaded_at")
        else:
            latest_ids = (
                docs_qs
                .values("year", "doc_type")
                .annotate(last_id=Max("id"))
                .values_list("last_id", flat=True)
            )
            docs = docs_qs.filter(id__in=latest_ids).order_by("-year", "doc_type")

        return JsonResponse({
            "scope": scope,
            "documents": [_serialize_document(doc) for doc in docs],
        })

    files = request.FILES.getlist("pdf_files") or request.FILES.getlist("files")
    if not files:
        return HttpResponseBadRequest("Chybí soubory k nahrání.")

    results = []
    for uploaded in files:
        try:
            result = _process_uploaded_file(request.user, uploaded)
            results.append({k: v for k, v in result.items() if k != "document"})
        except Exception as exc:  # pragma: no cover - log only
            print(f"[CHYBA API] {uploaded.name}: {exc}")
            results.append({
                "file": uploaded.name,
                "year": None,
                "type": None,
                "status": str(exc),
                "success": False,
            })

    overall_success = all(item.get("success") for item in results)
    return JsonResponse({"success": overall_success, "results": results}, status=201)


@login_required
@require_http_methods(["DELETE"])
def document_api(request, document_id: int):
    """Smaže dokument (a navázaný financial statement)."""
    doc = get_object_or_404(Document, id=document_id, owner=request.user)
    FinancialStatement.objects.filter(document=doc).delete()
    if doc.file:
        doc.file.delete(save=False)
    doc.delete()
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["POST"])
def upload_many_api(request):
    """JSON API pro multiupload (alias – používá documents_api)."""
    return documents_api(request)


@login_required
def process_pdf(request, document_id: int):
    """Ruční spuštění analýzy (fallback)."""
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    pdf_path = document.file.path

    if document.doc_type == "income":
        data = analyze_income(pdf_path)
    else:
        data = analyze_balance(pdf_path)

    _persist_statement(document, data)

    return redirect("dashboard:index")


@login_required
def delete_document(request, document_id: int):
    """Smaže dokument z HTML rozhraní."""
    doc = get_object_or_404(Document, id=document_id, owner=request.user)
    FinancialStatement.objects.filter(document=doc).delete()
    if doc.file:
        doc.file.delete(save=False)
    doc.delete()
    messages.success(request, "Dokument byl úspěšně smazán.")
    return redirect("ingest:documents")
