# Conversation Summary - Coach Module Implementation

## Date: 2025-12-06
## Branch: coachmodule

---

## Overview

This document summarizes the complete conversation thread that led to the implementation of the coach-client assignment system improvements, specifically focusing on handling unassigned users.

---

## Conversation Flow

### 1. Initial Git Operations
- Pushed dashboard modernization changes to GitHub
- Created commit and pushed to branch `grapf-remake`
- Merged changes to main branch
- Created new branch `coachmodule` for coach system work

### 2. Analysis Phase
**User Request**: "analyzuj a zkontroluj komunikaci mezi aplikaci coaching a dashboard. zjisti, jak funguje přiřazovaní koučů k uzivateli. navrhni jak opšetřit, pokud si uživatel behem onboarding nevybere kouče, jak mu jej potom přiřadit a jak na to upozornit. navrhni idealni dashboard pro coach roli"

**Output**: Created comprehensive analysis document `COACH_SYSTEM_PROPOSAL.md` with:
- System architecture analysis
- Current assignment flow diagrams
- Database schema documentation
- Proposals for unassigned user handling
- Coach dashboard improvement suggestions

### 3. Requirements Clarification
**User Clarification**:
- Coaches can already be selected during registration at `/accounts/register/`
- Need to show unassigned users in coach dashboard
- Coaches should be able to self-assign these users
- Users won't have ability to select coach after registration
- All coaches should see the same global pool of unassigned users

### 4. Implementation Phase

#### 4.1 URL Routing (`coaching/urls.py`)
Added new URL patterns:
```python
path("unassigned-users/", views.unassigned_users, name="unassigned_users"),
path("assign-client/<int:client_id>/", views.assign_client_to_self, name="assign_client"),
```

#### 4.2 Views (`coaching/views.py`)
Added two new views:

**`unassigned_users()`**:
- Displays list of users without assigned coach
- Filters out coaches themselves from the list
- Shows statistics (document count, days since registration, onboarding status)
- Global pool visible to all coaches

**`assign_client_to_self()`**:
- POST endpoint for self-assignment
- Validates coach permissions
- Checks client doesn't already have coach
- Assigns in both systems (legacy + new)
- Returns JSON for AJAX requests

**Modified `my_clients()`**:
- Added `unassigned_count` to context
- Used for badge display in dashboard

#### 4.3 Template Updates

**`modern_dashboard.html`**:
Added button in header:
```html
{% if unassigned_count > 0 %}
<a href="{% url 'coaching:unassigned_users' %}"
   class="inline-flex items-center gap-2 rounded-full bg-amber-500 text-white px-4 py-2">
  <svg>...</svg>
  Nepřiřazení ({{ unassigned_count }})
</a>
{% endif %}
```

**`unassigned_users.html`** (New):
- Full-page table of unassigned users
- Statistics columns (IČO, documents, days since registration, onboarding status)
- AJAX-based assignment with live updates
- Toast notifications
- Automatic row removal after assignment

### 5. Bug Fixes

#### 5.1 UTF-8 BOM Encoding Issue
**Problem**: Edit tool couldn't modify `coaching/views.py` due to UTF-8 with BOM encoding
**Solution**: Created Python script to append new views to file

#### 5.2 Coaches Appearing as Unassigned
**Problem**: One coach showed in unassigned users list
**User Feedback**: "nastav, aby uzivatel s právem/přístupem/funkcí coach se nezobrazoval jako nepřiřazený"
**Solution**: Added UserRole-based filtering:
```python
from accounts.models import UserRole
coach_user_ids = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)

unassigned = CompanyProfile.objects.filter(
    assigned_coach__isnull=True
).exclude(
    user__usercoachassignment__isnull=False
).exclude(
    user_id__in=coach_user_ids  # Filter out coaches
)
```

Applied to both:
- `unassigned_users()` view
- `my_clients()` view (for badge count)

---

## Technical Decisions

### 1. Dual Assignment System
Maintained backward compatibility by writing to both:
- **Legacy**: `CompanyProfile.assigned_coach` (ForeignKey to Coach)
- **New**: `UserCoachAssignment` (separate table with timestamps and notes)

### 2. Global Pool Approach
All coaches see the same unassigned users (first-come-first-served basis)
- Alternative rejected: Pre-assigned pools per coach
- Reasoning: Simpler, more flexible, encourages quick assignment

### 3. Security Layers
- `@login_required` - Only authenticated users
- `@coach_required` - Only coaches
- POST-only endpoint for assignments
- CSRF token validation
- Client doesn't already have coach check
- Exception handling

### 4. Performance Optimization
- `select_related('user')` to prevent N+1 queries
- `values_list('user_id', flat=True)` for efficient ID filtering

### 5. User Experience
- AJAX assignment with live updates
- Toast notifications
- Automatic row removal
- Badge with count in dashboard
- Confirmation dialog before assignment

---

## Files Modified/Created

### Modified Files
1. **`coaching/views.py`** - 96 lines added
   - New views: `unassigned_users()`, `assign_client_to_self()`
   - Modified: `my_clients()` with unassigned_count

2. **`coaching/urls.py`** - 3 lines added
   - Two new URL patterns for unassigned management
   - Home redirect pattern

3. **`templates/coaching/modern_dashboard.html`** - ~15 lines modified
   - Header section updated with "Nepřiřazení" button

### Created Files
1. **`templates/coaching/unassigned_users.html`** - 257 lines
   - Full template with table, AJAX, and styling

2. **`docs/COACH_UNASSIGNED_IMPLEMENTATION.md`** - 543 lines
   - Comprehensive implementation documentation

3. **`docs/COACH_SYSTEM_PROPOSAL.md`** - Created earlier
   - Initial analysis and proposal document

---

## Code Examples

### Unassigned Users Query
```python
from accounts.models import UserRole

# Get all coach user IDs
coach_user_ids = UserRole.objects.filter(role='coach').values_list('user_id', flat=True)

# Find unassigned users (excluding coaches)
unassigned = CompanyProfile.objects.filter(
    assigned_coach__isnull=True  # Legacy system
).exclude(
    user__usercoachassignment__isnull=False  # New system
).exclude(
    user_id__in=coach_user_ids  # Exclude coaches
).select_related('user').order_by('-created_at')
```

### Self-Assignment Logic
```python
@login_required
@coach_required
def assign_client_to_self(request, client_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    coach = get_object_or_404(Coach, user=request.user)
    client_profile = get_object_or_404(CompanyProfile, id=client_id)

    # Validate client doesn't have coach
    if client_profile.assigned_coach or UserCoachAssignment.objects.filter(client=client_profile.user).exists():
        return JsonResponse({'success': False, 'error': 'Tento klient již má přiřazeného kouče'}, status=400)

    try:
        # New system
        UserCoachAssignment.objects.create(
            coach=coach,
            client=client_profile.user,
            notes='Kouč si přiřadil klienta sám'
        )

        # Legacy system (backward compatibility)
        client_profile.assigned_coach = coach
        client_profile.save(update_fields=['assigned_coach'])

        return JsonResponse({
            'success': True,
            'client_name': client_profile.company_name,
            'redirect_url': '/coaching/my-clients/'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
```

### AJAX Assignment (Frontend)
```javascript
function assignClient(clientId, clientName) {
    if (!confirm(`Opravdu si chcete přiřadit klienta "${clientName}"?`)) {
        return;
    }

    fetch(`/coaching/assign-client/${clientId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(`Klient ${data.client_name} byl úspěšně přiřazen.`, 'success');

            // Remove row with animation
            const row = document.querySelector(`tr[data-client-id="${clientId}"]`);
            if (row) {
                row.style.opacity = '0';
                setTimeout(() => row.remove(), 300);
            }

            // Update counter
            const badge = document.querySelector('.unassigned-badge');
            if (badge) {
                const currentCount = parseInt(badge.textContent);
                badge.textContent = currentCount - 1;
            }
        } else {
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        showToast('Chyba při přiřazování klienta.', 'error');
    });
}
```

---

## Database Schema

### CompanyProfile (Legacy System)
```python
class CompanyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    assigned_coach = models.ForeignKey(Coach, null=True, blank=True, on_delete=models.SET_NULL)
    company_name = models.CharField(max_length=255)
    ico = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
```

### UserCoachAssignment (New System)
```python
class UserCoachAssignment(models.Model):
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE)
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
```

### UserRole
```python
class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    # roles: 'coach', 'company', 'admin'
```

---

## Git Commits

Branch: `coachmodule`

```
004240d - Add comprehensive documentation for unassigned users feature
7a41791 - Filter coaches from unassigned users list
61b43d4 - Add unassigned users management for coaches
6d53823 - Add material costs to dashboard & modernize chart design
```

---

## Testing Procedures

### Manual Testing

#### 1. Create Test User Without Coach
```python
python manage.py shell

from django.contrib.auth.models import User
from accounts.models import CompanyProfile, UserRole

user = User.objects.create_user(
    username='testfirma@example.com',
    email='testfirma@example.com',
    password='testpass123'
)

UserRole.objects.create(user=user, role='company')

CompanyProfile.objects.create(
    user=user,
    company_name='Test Firma s.r.o.',
    ico='12345678',
    contact_person='Jan Novák',
    phone='+420123456789',
    # assigned_coach=None  # No coach assigned
)
```

#### 2. Login as Coach
- Navigate to http://127.0.0.1:8000/accounts/login/
- Login with coach credentials
- Should redirect to `/coaching/my-clients/`

#### 3. Check Badge
- Header should show: "Nepřiřazení (1)"

#### 4. View Unassigned Users
- Click "Nepřiřazení" button
- Should see table with "Test Firma s.r.o."
- Verify statistics display

#### 5. Assign Client
- Click "Přiřadit" button
- Confirm dialog
- Row should disappear with animation
- Success toast should appear
- Badge count should decrease

#### 6. Verify Assignment
- Return to `/coaching/my-clients/`
- "Test Firma s.r.o." should be in client list

---

## Monitoring & Metrics

### Key Metrics
```python
from accounts.models import CompanyProfile
from coaching.models import UserCoachAssignment
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, F

# Unassigned count
unassigned = CompanyProfile.objects.filter(
    assigned_coach__isnull=True
).exclude(
    user__usercoachassignment__isnull=False
).count()

# Average time to assignment
avg_time = UserCoachAssignment.objects.annotate(
    time_to_assign=F('assigned_at') - F('client__date_joined')
).aggregate(avg=Avg('time_to_assign'))

# Self-assignments (last 7 days)
self_assigned = UserCoachAssignment.objects.filter(
    notes__icontains='Kouč si přiřadil klienta sám',
    assigned_at__gte=timezone.now() - timedelta(days=7)
).count()

print(f'Nepřiřazeno: {unassigned}')
print(f'Průměrná doba: {avg_time}')
print(f'Self-assignments (7d): {self_assigned}')
```

---

## Troubleshooting

### Problem: Badge shows wrong count
**Solution**: Check that `my_clients()` view includes `unassigned_count` in context and filters coaches

### Problem: 404 when clicking "Nepřiřazení"
**Solution**: Verify URL patterns in `coaching/urls.py`

### Problem: "Method not allowed" when assigning
**Solution**: Ensure AJAX request is POST, not GET

### Problem: CSRF token error
**Solution**: Verify `getCookie('csrftoken')` function in JavaScript

### Problem: Coaches appear in unassigned list
**Solution**: Verify UserRole-based filtering is applied in query

---

## Future Enhancements (v2)

- [ ] **Email Notifications** - Send email to coaches when new user registers without coach
- [ ] **Auto-Assignment** - Automatic assignment based on industry/location
- [ ] **Bulk Assignment** - Assign multiple clients at once
- [ ] **Coach Availability** - Respect `Coach.available` flag
- [ ] **Client Capacity** - Limit number of clients per coach
- [ ] **Assignment History** - Log who assigned whom and when
- [ ] **Filtering & Sorting** - Filter unassigned by industry, location, registration date
- [ ] **Search Functionality** - Search unassigned users by name, IČO

---

## Conclusion

The implementation successfully provides:

✅ Display of unassigned users to all coaches (global pool)
✅ Self-assignment functionality with one click
✅ Badge showing unassigned count in coach dashboard
✅ Proper filtering to exclude coaches from unassigned list
✅ AJAX-based assignment with live updates
✅ Dual system assignment (legacy + new)
✅ Security layers and validation
✅ Comprehensive documentation

All requested features have been implemented, tested, and documented.
