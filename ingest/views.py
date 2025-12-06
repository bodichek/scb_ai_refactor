import logging
import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from ingest.models import Document, FinancialStatement
from ingest.extraction.pdf_processor import PDFProcessor
from ingest.extraction.claude_extractor import FinancialExtractor

logger = logging.getLogger(__name__)


# ================================================================
#   VISION-BASED EXTRACTION (NEW)
# ================================================================
def _process_uploaded_file_vision(user, uploaded_file, check_only=False):
    """
    Nová vision-based extrakce:
    1. PDF → PNG
    2. Claude vidí PNG graficky
    3. Extrahuje data z "Běžné období"

    Args:
        user: Django User instance
        uploaded_file: Uploaded PDF file
        check_only: If True, only extract metadata (year, doc_type) without saving to DB
    """
    result: Dict[str, Any] = {
        "file": getattr(uploaded_file, "name", ""),
        "success": False,
        "error": None,
    }

    tmp_path = None

    try:
        # -------------------------
        # 1) Uložit dočasný PDF
        # -------------------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        # -------------------------
        # 2) PDF → PNG conversion
        # -------------------------
        logger.info(f"Converting PDF to PNG: {uploaded_file.name}")
        processor = PDFProcessor(dpi=300)
        png_bytes = processor.pdf_to_png(tmp_path, page_num=0)

        # Save PNG locally
        local_image_path = processor.save_png_local(png_bytes)
        logger.info(f"PNG saved to: {local_image_path}")

        # -------------------------
        # 3) Claude vision extraction
        # -------------------------
        logger.info("Extracting data with Claude vision API")
        extractor = FinancialExtractor()
        extraction_result = extractor.extract_from_png(png_bytes)

        if not extraction_result.get("success"):
            error_msg = extraction_result.get("error", "Extraction failed")
            logger.error(f"Extraction failed: {error_msg}")
            result["error"] = error_msg
            return result

        doc_type = extraction_result.get("doc_type")
        year = extraction_result.get("year")
        data = extraction_result.get("extracted_data") or {}
        scale = extraction_result.get("scale") or "units"
        confidence = extraction_result.get("confidence", 0.0)

        if not doc_type or not isinstance(year, int):
            msg = "PDF nebyl rozpoznán (typ nebo rok chybí)."
            logger.warning(f"{msg} Výstup: {extraction_result}")
            result["error"] = msg
            return result

        # If check_only mode, return metadata without saving
        if check_only:
            result.update({
                "success": True,
                "year": year,
                "doc_type": doc_type,
                "confidence": confidence,
                "check_only": True,
            })
            return result

        # -------------------------
        # 4) Uložit Document model
        # -------------------------
        doc = Document.objects.create(
            owner=user,
            file=uploaded_file,
            year=year,
            doc_type=doc_type,
            analyzed=True,
        )

        # -------------------------
        # 5) Uložit FinancialStatement
        # -------------------------
        fs, _ = FinancialStatement.objects.get_or_create(
            user=user,
            year=year,
            defaults={"document": doc},
        )

        # Aktualizovat data
        fs.document = doc
        fs.scale = scale
        fs.local_image_path = local_image_path
        fs.confidence = confidence

        # Uložit správná data
        if doc_type == "income_statement":
            fs.income = data
        elif doc_type == "balance_sheet":
            fs.balance = data

        fs.save()

        # -------------------------
        # 6) Výsledek pro uživatele
        # -------------------------
        result.update({
            "success": True,
            "year": year,
            "doc_type": doc_type,
            "status": "Analyzováno (Vision API)",
            "confidence": confidence,
            "local_image_path": local_image_path,
        })
        return result

    except Exception as exc:
        logger.error(f"Chyba při zpracování (vision): {uploaded_file}: {exc}", exc_info=True)
        result["error"] = str(exc)
        return result

    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ================================================================
#   1) Upload jednoho PDF (HTML) - Using Vision API
# ================================================================
@login_required
def upload_pdf(request):
    if request.method == "POST":
        file = request.FILES.get("pdf_file") or request.FILES.get("file")
        confirm_overwrite = request.POST.get("confirm_overwrite") == "yes"

        # Check if this is a confirmation of pending upload
        if confirm_overwrite and 'pending_upload' in request.session:
            pending = request.session['pending_upload']
            temp_path = pending.get('temp_path')

            if temp_path and os.path.exists(temp_path):
                # Create a file-like object from temp file
                from django.core.files import File
                with open(temp_path, 'rb') as temp_file:
                    django_file = File(temp_file, name=pending['file_name'])
                    result = _process_uploaded_file_vision(request.user, django_file, check_only=False)

                # Clean up temp file
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

                del request.session['pending_upload']

                if result["success"]:
                    confidence = result.get("confidence", 0)
                    conf_pct = int(confidence * 100)
                    messages.success(
                        request,
                        f"Soubor *{pending['file_name']}* byl úspěšně analyzován a data přepsána (confidence: {conf_pct}%)."
                    )
                    return redirect("dashboard:index")

                messages.error(request, result.get("error") or "Soubor se nepodařilo analyzovat.")
                return redirect("upload_pdf")
            else:
                messages.error(request, "Dočasný soubor nenalezen. Nahrajte soubor znovu.")
                del request.session['pending_upload']
                return redirect("upload_pdf")

        if not file:
            return JsonResponse({"error": "Soubor nebyl nahrán."}, status=400)

        # First, extract metadata without saving to DB
        result = _process_uploaded_file_vision(request.user, file, check_only=True)

        if not result["success"]:
            messages.error(request, result.get("error") or "Soubor se nepodařilo analyzovat.")
            return redirect("upload_pdf")

        year = result.get("year")
        doc_type = result.get("doc_type")
        confidence = result.get("confidence", 0)

        # Check if data already exists for this year and doc_type
        if not confirm_overwrite:
            existing_fs = FinancialStatement.objects.filter(
                user=request.user,
                year=year
            ).first()

            if existing_fs:
                # Check if the same doc_type already has data
                has_data = False
                doc_type_name = ""

                if doc_type == "income_statement" and existing_fs.income:
                    has_data = True
                    doc_type_name = "Výkaz zisku a ztráty (Výsledovka)"
                elif doc_type == "balance_sheet" and existing_fs.balance:
                    has_data = True
                    doc_type_name = "Rozvaha"

                if has_data:
                    # Save file temporarily and store path in session
                    temp_filename = f"temp_upload_{uuid.uuid4().hex}.pdf"
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, temp_filename)

                    with open(temp_path, 'wb') as temp_file:
                        for chunk in file.chunks():
                            temp_file.write(chunk)

                    request.session['pending_upload'] = {
                        'file_name': file.name,
                        'temp_path': temp_path,
                        'year': year,
                        'doc_type': doc_type,
                        'confidence': confidence,
                    }
                    return render(request, "ingest/upload_confirm.html", {
                        "file_name": file.name,
                        "year": year,
                        "doc_type": doc_type,
                        "doc_type_name": doc_type_name,
                        "new_confidence": int(confidence * 100),
                        "existing_confidence": int((existing_fs.confidence or 0) * 100),
                    })

        # Proceed with actual upload (either confirmed or no conflict)
        result = _process_uploaded_file_vision(request.user, file, check_only=False)

        if result["success"]:
            confidence = result.get("confidence", 0)
            conf_pct = int(confidence * 100)
            # Clear session data if exists
            if 'pending_upload' in request.session:
                del request.session['pending_upload']
            messages.success(
                request,
                f"Soubor *{file.name}* byl úspěšně analyzován (confidence: {conf_pct}%)."
            )
            return redirect("dashboard:index")

        messages.error(request, result.get("error") or "Soubor se nepodařilo analyzovat.")
        return redirect("upload_pdf")

    # GET request - show form with year options
    current_year = datetime.now().year
    years = list(range(current_year - 10, current_year + 2))
    return render(request, "ingest/upload.html", {"years": years})


# ================================================================
#   2) Upload více PDF (HTML) - Using Vision API
# ================================================================
@login_required
def upload_many(request):
    if request.method == "POST":
        files = request.FILES.getlist("pdf_files") or request.FILES.getlist("files")
        results = []

        for f in files:
            # Use vision-based extraction
            res = _process_uploaded_file_vision(request.user, f)
            if not res["success"]:
                logger.error(f"Chyba uploadu {f.name}: {res.get('error')}")
            results.append(res)

        return render(request, "ingest/upload_many_result.html", {"results": results})

    return render(request, "ingest/upload_many.html")


# ================================================================
#   3) Seznam dokumentů (HTML)
# ================================================================
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

    for doc in docs:
        fs = FinancialStatement.objects.filter(document=doc).first()
        doc.last_updated = getattr(fs, "created_at", None)

    return render(request, "ingest/documents_list.html", {"documents": docs, "show_all": show_all})


# ================================================================
#   4) API – seznam a upload
# ================================================================
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

    files = request.FILES.getlist("files")
    if not files:
        return HttpResponseBadRequest("Žádné soubory.")

    # Use vision-based extraction
    results = [
        _process_uploaded_file_vision(request.user, f)
        for f in files
    ]

    return JsonResponse({"results": results})


# ================================================================
#   4B) API – Vision-based extraction endpoint
# ================================================================
@login_required
@require_http_methods(["POST"])
def upload_vision_api(request):
    """
    New API endpoint specifically for vision-based extraction
    Returns detailed extraction results including confidence and PNG path
    """
    files = request.FILES.getlist("files") or [request.FILES.get("file")]
    files = [f for f in files if f]  # Filter out None values

    if not files:
        return HttpResponseBadRequest("Žádné soubory.")

    results = []
    for f in files:
        result = _process_uploaded_file_vision(request.user, f)
        results.append(result)

    # Return detailed results
    if len(results) == 1:
        return JsonResponse(results[0])
    else:
        return JsonResponse({"results": results})


# ================================================================
#   5) API DELETE dokumentu
# ================================================================
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


# ================================================================
#   7) DELETE dokumentu (HTML)
# ================================================================
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
