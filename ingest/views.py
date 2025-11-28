import logging
import os
import tempfile
from typing import Dict, Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from ingest.ai_parser_refactored import parse_financial_pdf
from ingest.models import Document, FinancialStatement

logger = logging.getLogger(__name__)


# ====================================================================
# HELPER – jednotná cesta pro upload + parsing (pro onboarding, upload, API)
# ====================================================================

def _process_uploaded_file(user, uploaded_file):
    import tempfile, os
    from ingest.models import Document, FinancialStatement

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        parsed = parse_financial_pdf(tmp_path)

        doc_type = parsed.get("doc_type")
        year = parsed.get("year")
        data = parsed.get("data", {})
        scale = parsed.get("scale", "units")

        if not doc_type or not year:
            raise ValueError("Parser nevrátil typ nebo rok.")

        # Document – pouzivas sve stare hodnoty (napr. income/balance),
        # pokud je treba, muzes tady namapovat:
        # doc_type_db = map_doc_type(doc_type)
        doc_type_db = doc_type  # pokud mas v DB uz nove nazvy

        doc = Document.objects.create(
            owner=user,
            file=uploaded_file,
            year=year,
            doc_type=doc_type_db,
            analyzed=True,
        )

        existing_fs = FinancialStatement.objects.filter(
            owner=user, year=year, doc_type=doc_type_db
        ).first()

        merged_data = {}
        if existing_fs and isinstance(existing_fs.data, dict):
            merged_data.update(existing_fs.data)
        for key, value in (data or {}).items():
            if value not in (None, 0):
                merged_data[key] = value

        merged_scale = scale or (existing_fs.scale if existing_fs else "units")

        FinancialStatement.objects.update_or_create(
            owner=user,
            year=year,
            doc_type=doc_type_db,
            defaults={
                "data": merged_data,
                "document": doc,
                "scale": merged_scale,
            },
        )

        return {
            "file": uploaded_file.name,
            "year": year,
            "type": doc_type_db,
            "status": "Analyzovano",
            "success": True,
        }

    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass



def _ensure_parsed(parsed: Dict[str, Any]):
    """Validační pomocník."""
    if not parsed.get("doc_type") or not parsed.get("year"):
        raise ValueError("Parser nevrátil typ nebo rok.")
    return parsed


# ====================================================================
# 1) Upload jednoho PDF (HTML)
# ====================================================================

@login_required
def upload_pdf(request):
    if request.method == "POST":
        file = request.FILES.get("pdf_file") or request.FILES.get("file")

        if not file:
            return JsonResponse({"error": "Soubor nebyl nahrán."}, status=400)

        try:
            result = _process_uploaded_file(request.user, file)
            messages.success(request, "Soubor byl úspěšně analyzován.")
            return redirect("dashboard:index")

        except Exception as e:
            logger.error(f"Chyba při nahrávání PDF: {e}", exc_info=True)
            messages.error(request, f"Chyba: {e}")
            return redirect("upload_pdf")

    return render(request, "ingest/upload.html")


# ====================================================================
# 2) Upload více PDF (HTML)
# ====================================================================

@login_required
def upload_many(request):
    if request.method == "POST":
        files = request.FILES.getlist("pdf_files") or request.FILES.getlist("files")
        results = []

        for f in files:
            try:
                res = _process_uploaded_file(request.user, f)
                results.append({
                    "file": f.name,
                    "success": True,
                    "year": res.get("year"),
                    "doc_type": res.get("doc_type"),
                })
            except Exception as e:
                logger.error(f"Chyba uploadu {f.name}: {e}", exc_info=True)
                results.append({"file": f.name, "success": False, "error": str(e)})

        return render(request, "ingest/upload_many_result.html", {"results": results})

    return render(request, "ingest/upload_many.html")


# ====================================================================
# 3) Seznam dokumentů (HTML)
# ====================================================================

@login_required
def documents_list(request):
    show_all = request.GET.get("vse") == "1"
    qs = Document.objects.filter(owner=request.user)

    if show_all:
        docs = qs.order_by("-year", "-uploaded_at")
    else:
        latest_ids = (
            qs.values("year", "doc_type")
            .annotate(last_id=Max("id"))
            .values_list("last_id", flat=True)
        )
        docs = qs.filter(id__in=latest_ids).order_by("-year")

    # poslední aktualizace
    for doc in docs:
        fs = FinancialStatement.objects.filter(document=doc).first()
        doc.last_updated = getattr(fs, "created_at", None)

    return render(request, "ingest/documents_list.html", {
        "documents": docs,
        "show_all": show_all,
    })


# ====================================================================
# 4) API – seznam a upload
# ====================================================================

@login_required
@require_http_methods(["GET", "POST"])
def documents_api(request):
    if request.method == "GET":
        scope = request.GET.get("scope", "latest")
        qs = Document.objects.filter(owner=request.user)

        if scope == "all":
            docs = qs.order_by("-year", "-uploaded_at")
        else:
            latest_ids = (
                qs.values("year", "doc_type")
                .annotate(last_id=Max("id"))
                .values_list("last_id", flat=True)
            )
            docs = qs.filter(id__in=latest_ids).order_by("-year")

        def serialize(doc):
            fs = FinancialStatement.objects.filter(document=doc).first()
            return {
                "id": doc.id,
                "filename": os.path.basename(doc.file.name),
                "year": doc.year,
                "doc_type": doc.doc_type,
                "analyzed": doc.analyzed,
                "uploaded_at": doc.uploaded_at.isoformat(),
                "last_updated": fs.created_at.isoformat() if fs else None,
                "scale": getattr(fs, "scale", None),
                "url": doc.file.url if doc.file else "",
            }

        return JsonResponse({"documents": [serialize(d) for d in docs]})

    # POST upload přes API
    files = request.FILES.getlist("files")
    if not files:
        return HttpResponseBadRequest("Žádné soubory.")

    results = []
    for f in files:
        try:
            res = _process_uploaded_file(request.user, f)
            results.append({"file": f.name, "success": True})
        except Exception as e:
            results.append({"file": f.name, "success": False, "error": str(e)})

    return JsonResponse({"results": results})


# ====================================================================
# 5) API DELETE
# ====================================================================

@login_required
@require_http_methods(["DELETE"])
def document_api(request, document_id):
    try:
        doc = get_object_or_404(Document, id=document_id, owner=request.user)

        FinancialStatement.objects.filter(document=doc).delete()
        if doc.file:
            doc.file.delete(save=False)
        doc.delete()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ====================================================================
# 6) Manuální re-analýza
# ====================================================================

@login_required
def process_pdf(request, document_id):
    try:
        doc = get_object_or_404(Document, id=document_id, owner=request.user)

        parsed = parse_financial_pdf(doc.file.path)
        parsed = _ensure_parsed(parsed)

        existing_fs = FinancialStatement.objects.filter(
            owner=request.user,
            year=parsed["year"],
            doc_type=parsed["doc_type"],
        ).first()

        merged_data = {}
        if existing_fs and isinstance(existing_fs.data, dict):
            merged_data.update(existing_fs.data)
        for key, value in (parsed.get("data") or {}).items():
            if value not in (None, 0):
                merged_data[key] = value

        merged_scale = parsed.get("scale") or (existing_fs.scale if existing_fs else "units")

        FinancialStatement.objects.update_or_create(
            owner=request.user,
            year=parsed["year"],
            doc_type=parsed["doc_type"],
            defaults={
                "data": merged_data,
                "document": doc,
                "scale": merged_scale,
            }
        )

        messages.success(request, "Dokument znovu analyzován.")
    except Exception as e:
        messages.error(request, f"Chyba: {e}")

    return redirect("ingest:documents")


# ====================================================================
# 7) DELETE dokumentu (HTML)
# ====================================================================

@login_required
def delete_document(request, document_id):
    try:
        doc = get_object_or_404(Document, id=document_id, owner=request.user)
        FinancialStatement.objects.filter(document=doc).delete()
        if doc.file:
            doc.file.delete(save=False)
        doc.delete()
        messages.success(request, "Dokument byl smazán.")
    except Exception as e:
        messages.error(request, f"Chyba při mazání: {e}")

    return redirect("ingest:documents")
