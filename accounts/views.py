from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import IntegrityError

from coaching.models import Coach
from .models import CompanyProfile, UserRole


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html")


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
        return redirect("accounts:edit_profile")

    coaches = Coach.objects.all()
    return render(request, "accounts/profile_form.html", {"profile": profile, "coaches": coaches})


def landing(request):
    return render(request, "base_landing.html")


def register(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        company_name = request.POST.get("company_name")
        ico = request.POST.get("ico")
        contact_person = request.POST.get("contact_person")
        phone = request.POST.get("phone")
        website = request.POST.get("website")
        linkedin = request.POST.get("linkedin")
        industry = request.POST.get("industry")
        employees_count = request.POST.get("employees_count") or None
        coach_id = request.POST.get("assigned_coach")

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
