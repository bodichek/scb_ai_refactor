from django.shortcuts import redirect

def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")
    return redirect("accounts:login")