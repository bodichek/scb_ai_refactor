from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from .models import OnboardingProgress


class OnboardingProgressMiddleware:
    """
    Redirect authenticated company users to the onboarding wizard until they finish it.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.step_order = [
            OnboardingProgress.Steps.UPLOAD,
            OnboardingProgress.Steps.SURVEY,
            OnboardingProgress.Steps.OPEN_SURVEY,
        ]
        self.step_to_url = {}
        self.url_to_step = {}
        self.exempt_paths = set(filter(None, [
            reverse("accounts:logout"),
            reverse("accounts:login"),
            reverse("accounts:register"),
        ]))
        self.exempt_prefixes = (
            "/admin/",
            "/static/",
            settings.MEDIA_URL if getattr(settings, "MEDIA_URL", None) else "/media/",
        )
        self._ensure_step_urls()

    def _ensure_step_urls(self):
        if self.step_to_url:
            return
        try:
            self.step_to_url = {
                OnboardingProgress.Steps.UPLOAD: reverse("onboarding:upload"),
                OnboardingProgress.Steps.SURVEY: reverse("onboarding:survey"),
                OnboardingProgress.Steps.OPEN_SURVEY: reverse("onboarding:open_survey"),
            }
            self.url_to_step = {url: step for step, url in self.step_to_url.items()}
            self.exempt_paths.update(self.step_to_url.values())
            self.exempt_paths.add(reverse("onboarding:start"))
        except Exception:
            # reverse may fail before URL conf is ready; we'll try again on next call
            self.step_to_url = {}
            self.url_to_step = {}

    def _step_index(self, step):
        try:
            return self.step_order.index(step)
        except ValueError:
            return len(self.step_order)

    def __call__(self, request):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return self.get_response(request)

        if user.is_staff or user.is_superuser:
            return self.get_response(request)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return self.get_response(request)

        if request.method == "OPTIONS":
            return self.get_response(request)

        path = request.path or "/"

        for prefix in self.exempt_prefixes:
            if prefix and path.startswith(prefix):
                return self.get_response(request)

        self._ensure_step_urls()

        role = getattr(getattr(user, "userrole", None), "role", "company")
        if role == "coach":
            return self.get_response(request)

        progress, _ = OnboardingProgress.objects.get_or_create(user=user)

        if progress.is_completed or progress.current_step == OnboardingProgress.Steps.DONE:
            return self.get_response(request)

        # Allow visiting onboarding steps up to the current progress (inclusive)
        if path in self.url_to_step:
            requested_step = self.url_to_step[path]
            requested_index = self._step_index(requested_step)
            current_index = self._step_index(progress.current_step)

            if requested_index > current_index:
                target_url = self.step_to_url.get(progress.current_step, self.step_to_url.get(self.step_order[0]))
                if target_url and target_url != path:
                    return redirect(target_url)
            return self.get_response(request)

        # Allow the onboarding landing route to resolve current step
        onboarding_start = reverse("onboarding:start")
        if path == onboarding_start:
            return self.get_response(request)

        # Block access to other routes until onboarding is done
        target_url = self.step_to_url.get(progress.current_step) or onboarding_start
        return redirect(target_url)
