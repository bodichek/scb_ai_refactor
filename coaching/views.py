from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Coach


@login_required
def my_clients(request):
    return render(request, "coaching/my_clients.html")
@login_required
def edit_coach(request):
    coach, _ = Coach.objects.get_or_create(user=request.user)

    if request.method == "POST":
        coach.specialization = request.POST.get("specialization")
        coach.bio = request.POST.get("bio")
        coach.phone = request.POST.get("phone")
        coach.email = request.POST.get("email")
        coach.linkedin = request.POST.get("linkedin")
        coach.website = request.POST.get("website")
        coach.city = request.POST.get("city")
        coach.available = bool(request.POST.get("available"))
        coach.save()
        return redirect("my_clients")

    return render(request, "coaching/coach_form.html", {"coach": coach})