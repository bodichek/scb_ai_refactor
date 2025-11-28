from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.models import OnboardingProgress
from ingest.views import _process_uploaded_file
from survey.models import Response, SurveySubmission
from survey.views import QUESTIONS as SURVEY_QUESTIONS, generate_ai_summary
from suropen.views import (
    QUESTIONS as SUROPEN_QUESTIONS,
    DuplicateSubmissionError,
    NoAnswerProvided,
    _create_submission,
)
from suropen.models import OpenAnswer


# ============================================================
# Wizard step definitions
# ============================================================

WIZARD_STEPS = [
    {"id": OnboardingProgress.Steps.UPLOAD, "label": "Nahrát PDF"},
    {"id": OnboardingProgress.Steps.SURVEY, "label": "Firemní dotazník"},
    {"id": OnboardingProgress.Steps.OPEN_SURVEY, "label": "Otevřený dotazník"},
    {"id": OnboardingProgress.Steps.DONE, "label": "Hotovo"},
]

SURVEY_QUESTION_INDEX = {q["question"]: i for i, q in enumerate(SURVEY_QUESTIONS)}


# ============================================================
# Helper utilities
# ============================================================

def _get_progress(user):
    progress, _ = OnboardingProgress.objects.get_or_create(user=user)
    return progress


def _wizard_context(request, step: OnboardingProgress.Steps, **extra):
    progress = _get_progress(request.user)

    step_index_map = {item["id"]: idx for idx, item in enumerate(WIZARD_STEPS)}
    current_index = step_index_map.get(progress.current_step, 0)

    if progress.current_step == OnboardingProgress.Steps.DONE:
        current_index = len(WIZARD_STEPS) - 1

    total_steps = len(WIZARD_STEPS)
    progress_percent = int(round((current_index / (total_steps - 1)) * 100))

    base = {
        "step": step,
        "progress": progress,
        "wizard_steps": WIZARD_STEPS,
        "current_index": current_index,
        "progress_percent": progress_percent,
        "total_questions": len(SURVEY_QUESTIONS),
    }

    base.update(extra)
    return base


def _build_survey_sections():
    sections = []
    for idx, q in enumerate(SURVEY_QUESTIONS):
        cat = q.get("category", f"Blok {idx+1}")
        if not sections or sections[-1]["title"] != cat:
            sections.append({"title": cat, "questions": []})

        sections[-1]["questions"].append({
            "index": idx,
            "question": q["question"],
            "labels": q.get("labels", {}),
        })
    return sections


def _build_survey_prefill(sub):
    if not sub:
        return {}
    prefill = {}
    for r in sub.responses.all():
        idx = SURVEY_QUESTION_INDEX.get(r.question)
        if idx is not None:
            prefill[f"q{idx}"] = r.score
    return prefill


def _build_open_prefill(user, batch_id):
    if not batch_id:
        return {}
    answers = OpenAnswer.objects.filter(user=user, batch_id=batch_id)

    answer_map = {(a.section, a.question): a.answer for a in answers}
    prefill = {}

    for s_i, block in enumerate(SUROPEN_QUESTIONS):
        for q_i, qtext in enumerate(block["items"]):
            key = f"q-{s_i}-{q_i}"
            prefill[key] = answer_map.get((block["section"], qtext), "")

    return prefill


def _redirect_for_progress(progress):
    if progress.current_step == OnboardingProgress.Steps.DONE:
        return reverse("dashboard:index")

    return {
        OnboardingProgress.Steps.UPLOAD: reverse("onboarding:upload"),
        OnboardingProgress.Steps.SURVEY: reverse("onboarding:survey"),
        OnboardingProgress.Steps.OPEN_SURVEY: reverse("onboarding:open_survey"),
    }.get(progress.current_step, reverse("onboarding:upload"))


# ============================================================
# Entry point
# ============================================================

@login_required
def entrypoint(request):
    progress = _get_progress(request.user)
    return redirect(_redirect_for_progress(progress))


# ============================================================
# STEP 1: UPLOAD PDF
# ============================================================

@login_required
def upload_step(request):
    progress = _get_progress(request.user)
    origin_step = progress.current_step

    if request.method == "POST":
        files = request.FILES.getlist("pdf_file")
        if not files:
            messages.error(request, "Vyberte prosím alespoň jeden PDF soubor.")
        else:
            success = 0
            for f in files:
                try:
                    _process_uploaded_file(request.user, f)
                    success += 1
                except Exception as exc:
                    messages.error(request, f"Soubor {f.name} selhal: {exc}")

            if success:
                # Move wizard forward
                if origin_step == OnboardingProgress.Steps.UPLOAD:
                    progress.mark_step(OnboardingProgress.Steps.SURVEY)
                    messages.success(request, f"Nahráno {success} souborů. Pokračujeme.")
                    return redirect("onboarding:survey")

                progress.mark_step(origin_step)
                messages.success(request, f"Úspěšně zpracováno {success} souborů.")

    ctx = _wizard_context(request, OnboardingProgress.Steps.UPLOAD)
    return render(request, "onboarding/onboarding_wizard.html", ctx)


# ============================================================
# STEP 2: SURVEY
# ============================================================

@login_required
def survey_step(request):
    progress = _get_progress(request.user)
    origin_step = progress.current_step

    if origin_step == OnboardingProgress.Steps.UPLOAD:
        return redirect("onboarding:upload")

    submission = progress.survey_submission or SurveySubmission.objects.filter(
        user=request.user
    ).order_by("-created_at").first()

    if submission:
        if not progress.survey_submission:
            progress.survey_submission = submission
            progress.save(update_fields=["survey_submission", "updated_at"])

    if request.method == "POST":
        with transaction.atomic():
            if submission:
                submission.responses.all().delete()
            else:
                submission = SurveySubmission.objects.create(user=request.user)

            for idx, q in enumerate(SURVEY_QUESTIONS):
                raw = request.POST.get(f"q{idx}", "5")
                try:
                    score = max(1, min(10, int(raw)))
                except:
                    score = 5
                Response.objects.create(
                    user=request.user,
                    submission=submission,
                    question=q["question"],
                    score=score,
                )

        generate_ai_summary(submission)

        if origin_step == OnboardingProgress.Steps.SURVEY:
            progress.mark_step(OnboardingProgress.Steps.OPEN_SURVEY, survey_submission=submission)
            return redirect("onboarding:open_survey")

        progress.mark_step(origin_step, survey_submission=submission)
        messages.success(request, "Dotazník uložen.")

    ctx = _wizard_context(
        request,
        OnboardingProgress.Steps.SURVEY,
        survey_sections=_build_survey_sections(),
        prefill_scores=_build_survey_prefill(submission),
    )
    return render(request, "onboarding/onboarding_wizard.html", ctx)


# ============================================================
# STEP 3: SUROPEN (OPEN QUESTIONS)
# ============================================================

@login_required
def open_survey_step(request):
    progress = _get_progress(request.user)
    origin_step = progress.current_step

    if origin_step == OnboardingProgress.Steps.UPLOAD:
        return redirect("onboarding:upload")
    if origin_step == OnboardingProgress.Steps.SURVEY:
        return redirect("onboarding:survey")

    batch_id = progress.suropen_batch_id
    if batch_id is None:
        last = OpenAnswer.objects.filter(user=request.user).order_by("-created_at").first()
        if last:
            batch_id = last.batch_id
            progress.suropen_batch_id = batch_id
            progress.save(update_fields=["suropen_batch_id", "updated_at"])

    prefill = _build_open_prefill(request.user, batch_id)

    if request.method == "POST":
        answers = []
        for s_i, block in enumerate(SUROPEN_QUESTIONS):
            for q_i, qtext in enumerate(block["items"]):
                key = f"q-{s_i}-{q_i}"
                answers.append({
                    "section": block["section"],
                    "question": qtext,
                    "answer": (request.POST.get(key) or "").strip(),
                })

        try:
            new_batch, _ = _create_submission(
                request.user,
                answers,
                existing_batch_id=batch_id,
                ignore_cooldown=batch_id is not None,
            )
        except NoAnswerProvided:
            messages.error(request, "Vyplň alespoň jednu odpověď.")
        except DuplicateSubmissionError:
            messages.warning(request, "Formulář byl odeslán příliš rychle.")
        except Exception as exc:
            messages.error(request, f"Chyba: {exc}")
        else:
            progress.mark_step(
                OnboardingProgress.Steps.DONE,
                suropen_batch_id=new_batch,
                completed=True,
            )
            messages.success(request, "Onboarding je dokončen.")
            return redirect("dashboard:index")

    ctx = _wizard_context(
        request,
        OnboardingProgress.Steps.OPEN_SURVEY,
        suropen_questions=SUROPEN_QUESTIONS,
        prefill_open_answers=prefill,
    )
    return render(request, "onboarding/onboarding_wizard.html", ctx)
