from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from accounts.models import CompanyProfile

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Potvrzení hesla")

    company_name = forms.CharField(label="Název firmy")
    ico = forms.CharField(label="IČO")
    contact_person = forms.CharField(label="Kontaktní osoba")
    phone = forms.CharField(label="Telefon")
    industry = forms.CharField(label="Odvětví působnosti")
    employees_count = forms.IntegerField(label="Počet zaměstnanců")
    linkedin = forms.URLField(label="LinkedIn", required=False)
    website = forms.URLField(label="Webové stránky", required=False)

    class Meta:
        model = User
        fields = ["email", "password"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Tento e-mail je již registrován.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Hesla se neshodují.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.username = email  # ✅ nastavení username = email (Django to vyžaduje)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            CompanyProfile.objects.create(
                user=user,
                company_name=self.cleaned_data["company_name"],
                ico=self.cleaned_data["ico"],
                contact_person=self.cleaned_data["contact_person"],
                phone=self.cleaned_data["phone"],
                industry=self.cleaned_data["industry"],
                employees_count=self.cleaned_data["employees_count"],
                linkedin=self.cleaned_data.get("linkedin", ""),
                website=self.cleaned_data.get("website", ""),
            )
        return user
