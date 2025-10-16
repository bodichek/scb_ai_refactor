from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.contrib.auth.models import User
from accounts.models import UserRole, CompanyProfile
from coaching.models import Coach, UserCoachAssignment


def get_user_role(user):
    """Získá roli uživatele"""
    try:
        user_role = UserRole.objects.get(user=user)
        return user_role.role
    except UserRole.DoesNotExist:
        return 'company'  # default role


def is_coach(user):
    """Kontrola, zda je uživatel coach"""
    return get_user_role(user) == 'coach'


def is_company(user):
    """Kontrola, zda je uživatel firma"""
    return get_user_role(user) == 'company'


def coach_required(view_func):
    """Decorator pro views dostupné pouze coachům"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not is_coach(request.user):
            messages.error(request, "Přístup povolen pouze coachům.")
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def company_required(view_func):
    """Decorator pro views dostupné pouze firmám"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not is_company(request.user):
            messages.error(request, "Přístup povolen pouze firmám.")
            return redirect('coaching:my_clients')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def get_coach_clients(coach_user):
    """Získá všechny klienty daného kouče přes UserCoachAssignment"""
    try:
        coach = Coach.objects.get(user=coach_user)
        assignments = UserCoachAssignment.objects.filter(coach=coach).values_list('client_id', flat=True)
        return User.objects.filter(id__in=assignments)
    except Coach.DoesNotExist:
        return User.objects.none()


def can_coach_access_client(coach_user, client_user_or_profile):
    """Kontrola, zda může coach přistupovat k datům klienta přes UserCoachAssignment"""
    if not is_coach(coach_user):
        return False
    
    try:
        coach = Coach.objects.get(user=coach_user)
        
        # Accept both User objects and CompanyProfile objects
        if hasattr(client_user_or_profile, 'user'):
            # It's a CompanyProfile
            client_user = client_user_or_profile.user
        else:
            # It's a User object
            client_user = client_user_or_profile
        
        # Zkontroluj přes UserCoachAssignment
        return UserCoachAssignment.objects.filter(coach=coach, client=client_user).exists()
    except Coach.DoesNotExist:
        return False


def coach_client_required(view_func):
    """
    Decorator pro views kde coach potřebuje přístup ke konkrétnímu klientovi.
    Očekává 'client_id' v URL parametrech.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, client_id, *args, **kwargs):
        if not is_coach(request.user):
            messages.error(request, "Přístup povolen pouze coachům.")
            return redirect('dashboard:index')
        
        # Najdi klienta
        client_profile = get_object_or_404(CompanyProfile, id=client_id)
        
        # Zkontroluj oprávnění
        if not can_coach_access_client(request.user, client_profile.user):
            messages.error(request, "Nemáte oprávnění k tomuto klientovi.")
            return redirect('coaching:my_clients')
        
        # Přidej klienta do kontextu
        kwargs['client_profile'] = client_profile
        return view_func(request, client_id, *args, **kwargs)
    return _wrapped_view


def get_accessible_user(request_user, target_user_id=None):
    """
    Získá uživatele, ke kterému má přihlášený uživatel přístup.
    - Firma vidí jen sebe
    - Coach vidí své klienty + sebe
    """
    if target_user_id is None:
        return request_user
    
    if is_company(request_user):
        # Firma vidí jen sebe
        if str(request_user.id) == str(target_user_id):
            return request_user
        else:
            raise Http404("Nemáte oprávnění k těmto datům.")
    
    elif is_coach(request_user):
        # Coach vidí sebe nebo své klienty
        if str(request_user.id) == str(target_user_id):
            return request_user
        
        # Zkontroluj, zda je target_user klientem tohoto kouče
        try:
            target_user = User.objects.get(id=target_user_id)
            if can_coach_access_client(request_user, target_user):
                return target_user
        except User.DoesNotExist:
            pass
        
        raise Http404("Nemáte oprávnění k těmto datům.")
    
    else:
        raise Http404("Neznámá role uživatele.")