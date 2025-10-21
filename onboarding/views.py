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


WIZARD_STEPS = [
    {"id": OnboardingProgress.Steps.UPLOAD, "label": "Nahrát PDF"},
    {"id": OnboardingProgress.Steps.SURVEY, "label": "Firemní dotazník"},
    {"id": OnboardingProgress.Steps.OPEN_SURVEY, "label": "Otevřený dotazník"},
    {"id": OnboardingProgress.Steps.DONE, "label": "Hotovo"},
]

SURVEY_QUESTION_INDEX = {question["question"]: idx for idx, question in enumerate(SURVEY_QUESTIONS)}


def _get_progress(user):
    progress, _ = OnboardingProgress.objects.get_or_create(user=user)
    return progress


def _wizard_context(request, step: OnboardingProgress.Steps, **extra):
    progress = _get_progress(request.user)

    step_index_map = {item["id"]: idx for idx, item in enumerate(WIZARD_STEPS)}
    current_index = step_index_map.get(progress.current_step, 0)
    if progress.is_completed or progress.current_step == OnboardingProgress.Steps.DONE:
        current_index = len(WIZARD_STEPS) - 1

    total_steps = len(WIZARD_STEPS)
    if total_steps <= 1:
        progress_percent = 100
    else:
        progress_percent = int(round((current_index / (total_steps - 1)) * 100))

    base_context = {
        "step": step,
        "progress": progress,
        "wizard_steps": WIZARD_STEPS,
        "current_index": current_index,
        "progress_percent": progress_percent,
    }
    base_context.update(extra)
    base_context.setdefault("prefill_scores", {})
    base_context.setdefault("prefill_open_answers", {})
    base_context.setdefault("total_questions", len(SURVEY_QUESTIONS))
    return base_context


def _build_survey_sections():
    sections = []
    for idx, question in enumerate(SURVEY_QUESTIONS):
        category = question.get("category") or f"Blok {idx + 1}"
        if not sections or sections[-1]["title"] != category:
            sections.append({"title": category, "questions": []})
        sections[-1]["questions"].append(
            {
                "index": idx,
                "question": question["question"],
                "labels": question.get("labels", {}),
            }
        )
    return sections


def _build_survey_prefill(submission: SurveySubmission | None) -> dict[str, int]:
    if not submission:
        return {}
    prefill = {}
    responses = submission.responses.all()
    for response in responses:
        idx = SURVEY_QUESTION_INDEX.get(response.question)
        if idx is not None:
            prefill[f"q{idx}"] = response.score
    return prefill


def _build_open_prefill(user, batch_id) -> dict[str, str]:
    if not batch_id:
        return {}
    answers = OpenAnswer.objects.filter(user=user, batch_id=batch_id)
    answer_map = {(a.section, a.question): a.answer for a in answers}
    prefill = {}
    for section_index, block in enumerate(SUROPEN_QUESTIONS):
        for question_index, question_text in enumerate(block["items"]):
            key = f"q-{section_index}-{question_index}"
            prefill[key] = answer_map.get((block["section"], question_text), "")
    return prefill


def _redirect_for_progress(progress: OnboardingProgress):
    if progress.is_completed or progress.current_step == OnboardingProgress.Steps.DONE:
        return reverse("dashboard:index")
    return {
        OnboardingProgress.Steps.UPLOAD: reverse("onboarding:upload"),
        OnboardingProgress.Steps.SURVEY: reverse("onboarding:survey"),
        OnboardingProgress.Steps.OPEN_SURVEY: reverse("onboarding:open_survey"),
    }.get(progress.current_step, reverse("onboarding:upload"))


@login_required
def entrypoint(request):
    progress = _get_progress(request.user)
    return redirect(_redirect_for_progress(progress))


@login_required
def upload_step(request):
    progress = _get_progress(request.user)
    origin_step = progress.current_step

    if request.method == "POST":
        uploaded_files = request.FILES.getlist("pdf_file")
        if not uploaded_files:
            messages.error(request, "Vyberte prosím alespoň jeden PDF soubor k nahrání.")
        else:
            successful = 0
            for uploaded in uploaded_files:
                try:
                    _process_uploaded_file(request.user, uploaded)
                    successful += 1
                except Exception as exc:  # pragma: no cover - log only
                    messages.error(
                        request,
                        f"Nahrání souboru {uploaded.name} se nezdařilo: {exc}",
                    )

            if successful:
                if origin_step == OnboardingProgress.Steps.UPLOAD:
                    progress.mark_step(OnboardingProgress.Steps.SURVEY)
                    messages.success(
                        request,
                        f"Nahráno {successful} souborů. Pokračujme na dotazník.",
                    )
                    return redirect("onboarding:survey")
                elif progress.is_completed:
                    progress.mark_step(OnboardingProgress.Steps.DONE, completed=True)
                else:
                    progress.mark_step(origin_step)

                messages.success(
                    request,
                    f"Úspěšně zpracováno {successful} souborů.",
                )

    context = _wizard_context(request, OnboardingProgress.Steps.UPLOAD)
    return render(request, "onboarding/onboarding_wizard.html", context)


@login_required
def survey_step(request):
    progress = _get_progress(request.user)
    origin_step = progress.current_step
    origin_completed = progress.is_completed

    if origin_step == OnboardingProgress.Steps.UPLOAD:
        return redirect("onboarding:upload")

    existing_submission = progress.survey_submission
    if existing_submission is None:
        existing_submission = (
            SurveySubmission.objects.filter(user=request.user).order_by("-created_at").first()
        )
        if existing_submission:
            progress.survey_submission = existing_submission
            progress.save(update_fields=["survey_submission", "updated_at"])

    if request.method == "POST":
        try:
            with transaction.atomic():
                if existing_submission:
                    submission = existing_submission
                    submission.responses.all().delete()
                else:
                    submission = SurveySubmission.objects.create(user=request.user)

                for idx, question in enumerate(SURVEY_QUESTIONS):
                    raw_value = request.POST.get(f"q{idx}", "5")
                    try:
                        score = max(1, min(10, int(raw_value)))
                    except (TypeError, ValueError):
                        score = 5
                    Response.objects.create(
                        user=request.user,
                        submission=submission,
                        question=question["question"],
                        score=score,
                    )
            generate_ai_summary(submission)

            if origin_completed:
                progress.mark_step(
                    OnboardingProgress.Steps.DONE,
                    survey_submission=submission,
                    completed=True,
                )
                messages.success(request, "Dotazník byl aktualizován.")
                return redirect("onboarding:survey")

            if origin_step == OnboardingProgress.Steps.SURVEY:
                progress.mark_step(
                    OnboardingProgress.Steps.OPEN_SURVEY,
                    survey_submission=submission,
                )
                return redirect("onboarding:open_survey")

            progress.mark_step(origin_step, survey_submission=submission)
            messages.success(request, "Dotazník byl aktualizován.")
            return redirect("onboarding:survey")
        except Exception as exc:  # pragma: no cover - log only
            messages.error(request, f"Nepodařilo se uložit dotazník: {exc}")

    context = _wizard_context(
        request,
        OnboardingProgress.Steps.SURVEY,
        survey_sections=_build_survey_sections(),
        total_questions=len(SURVEY_QUESTIONS),
        prefill_scores=_build_survey_prefill(existing_submission),
    )
    return render(request, "onboarding/onboarding_wizard.html", context)


@login_required
def open_survey_step(request):
    progress = _get_progress(request.user)
    origin_step = progress.current_step
    origin_completed = progress.is_completed

    if origin_step == OnboardingProgress.Steps.UPLOAD:
        return redirect("onboarding:upload")
    if origin_step == OnboardingProgress.Steps.SURVEY:
        return redirect("onboarding:survey")

    existing_batch_id = progress.suropen_batch_id
    if existing_batch_id is None:
        last_answer = OpenAnswer.objects.filter(user=request.user).order_by("-created_at").first()
        if last_answer:
            existing_batch_id = last_answer.batch_id
            progress.suropen_batch_id = existing_batch_id
            progress.save(update_fields=["suropen_batch_id", "updated_at"])
    prefill_open_answers = _build_open_prefill(request.user, existing_batch_id)

    if request.method == "POST":
        answers = []
        for section_index, block in enumerate(SUROPEN_QUESTIONS):
            for question_index, question_text in enumerate(block["items"]):
                key = f"q-{section_index}-{question_index}"
                answers.append(
                    {
                        "section": block["section"],
                        "question": question_text,
                        "answer": (request.POST.get(key) or "").strip(),
                    }
                )
        try:
            batch_id, _ = _create_submission(
                request.user,
                answers,
                existing_batch_id=existing_batch_id,
                ignore_cooldown=existing_batch_id is not None,
            )
        except NoAnswerProvided:
            messages.error(request, "Vyplň alespoň jednu odpověď, abychom mohli pokračovat.")
        except DuplicateSubmissionError:
            messages.warning(request, "Formulář byl odeslán příliš rychle po sobě. Zkus to prosím znovu.")
        except Exception as exc:  # pragma: no cover - log only
            messages.error(request, f"Nepodařilo se uložit odpovědi: {exc}")
        else:
            if origin_completed:
                progress.mark_step(
                    OnboardingProgress.Steps.DONE,
                    suropen_batch_id=batch_id,
                    completed=True,
                )
                messages.success(request, "Odpovědi byly aktualizovány.")
                return redirect("onboarding:open_survey")

            progress.mark_step(
                OnboardingProgress.Steps.DONE,
                suropen_batch_id=batch_id,
                completed=True,
            )
            messages.success(request, "Onboarding je dokončen. Vítej v SCB!")
            return redirect("dashboard:index")

    context = _wizard_context(
        request,
        OnboardingProgress.Steps.OPEN_SURVEY,
        suropen_questions=SUROPEN_QUESTIONS,
        prefill_open_answers=prefill_open_answers,
    )
    return render(request, "onboarding/onboarding_wizard.html", context)
