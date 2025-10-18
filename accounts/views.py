from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from coaching.models import Coach
from .models import CompanyProfile, UserRole


def login_view(request):
    """Vlastní login view s přesměrováním podle role uživatele"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Zkontroluj, jestli je uživatel kouč
            try:
                user_role = user.userrole.role
                if user_role == 'coach':
                    return redirect('coaching:my_clients')
                else:
                    return redirect('dashboard:index')
            except:
                # Pokud userrole neexistuje, přesměruj na dashboard
                return redirect('dashboard:index')
        else:
            messages.error(request, 'Neplatné přihlašovací údaje.')
    
    return render(request, 'accounts/login.html')


@csrf_exempt
@require_http_methods(["POST"])
def login_api(request):
    """JSON login endpoint pro SPA frontend."""
    try:
        if request.headers.get("Content-Type", "").startswith("application/json"):
            payload = json.loads((request.body or b"{}").decode("utf-8"))
        else:
            payload = request.POST
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON body.")

    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        return JsonResponse({"success": False, "error": "Vyplňte e-mail i heslo."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"success": False, "error": "Neplatné přihlašovací údaje."}, status=400)

    login(request, user)

    redirect_url = reverse("dashboard:index")
    try:
        user_role = user.userrole.role
        if user_role == "coach":
            redirect_url = reverse("coaching:my_clients")
    except Exception:
        pass

    return JsonResponse({"success": True, "redirect": redirect_url})


@login_required
def profile_view(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.company_name = request.POST.get("company_name")
        profile.ico = request.POST.get("ico")
        profile.contact_person = request.POST.get("contact_person")
        profile.phone = request.POST.get("phone")
        profile.email = request.POST.get("email")
        profile.website = request.POST.get("website")
        profile.linkedin = request.POST.get("linkedin")
        profile.industry = request.POST.get("industry")
        profile.employees_count = request.POST.get("employees_count") or None
        profile.save()
        return redirect("accounts:profile")

    return render(request, "accounts/profile.html", {"profile": profile})


@login_required
def edit_profile(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.company_name = request.POST.get("company_name")
        profile.ico = request.POST.get("ico")
        profile.contact_person = request.POST.get("contact_person")
        profile.phone = request.POST.get("phone")
        profile.email = request.POST.get("email")
        profile.website = request.POST.get("website")
        profile.linkedin = request.POST.get("linkedin")
        profile.industry = request.POST.get("industry")
        profile.employees_count = request.POST.get("employees_count") or None
        coach_id = request.POST.get("assigned_coach")
        profile.assigned_coach_id = coach_id if coach_id else None
        profile.save()
        # ✅ Po uložení přesměrování zpět na profil
        return redirect("accounts:profile")

    coaches = Coach.objects.all()
    return render(request, "accounts/profile_form.html", {"profile": profile, "coaches": coaches})


def landing(request):
    return render(request, "home.html")


def register(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        company_name = request.POST.get("company_name")
        ico = request.POST.get("ico")
        legal_form = request.POST.get("legal_form")
        address = request.POST.get("address")
        city = request.POST.get("city")
        postal_code = request.POST.get("postal_code")
        contact_person = request.POST.get("contact_person")
        phone = request.POST.get("phone")
        website = request.POST.get("website")
        linkedin = request.POST.get("linkedin")
        industry = request.POST.get("industry")
        employees_count = request.POST.get("employees_count") or None
        coach_id = request.POST.get("assigned_coach")

        # Validace hesla
        if len(password) < 8:
            messages.error(request, "Heslo musí mít alespoň 8 znaků.")
            return redirect("accounts:register")
        
        if password != password2:
            messages.error(request, "Hesla se neshodují.")
            return redirect("accounts:register")

        if User.objects.filter(username=email).exists():
            messages.error(request, "Tento e-mail je již registrován.")
            return redirect("accounts:register")

        try:
            user = User.objects.create_user(
                username=email,
                password=password,
                email=email,
            )
        except IntegrityError:
            messages.error(request, "Registrace selhala – e-mail už je použitý.")
            return redirect("accounts:register")

        UserRole.objects.create(user=user, role="company")
        CompanyProfile.objects.create(
            user=user,
            company_name=company_name,
            ico=ico,
            legal_form=legal_form,
            address=address,
            city=city,
            postal_code=postal_code,
            contact_person=contact_person,
            phone=phone,
            email=email,
            website=website,
            linkedin=linkedin,
            industry=industry,
            employees_count=employees_count,
            assigned_coach_id=coach_id if coach_id else None,
        )

        login(request, user)
        return redirect("dashboard:index")

    coaches = Coach.objects.all()
    return render(request, "accounts/register.html", {"coaches": coaches})

@login_required
def logout_view(request):
    """Odhlásí uživatele (funguje i na GET) a přesměruje na login."""
    logout(request)
    return redirect("accounts:login")  # nebo "home"
