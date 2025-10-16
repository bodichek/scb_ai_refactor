#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User

# Nastavíme heslo pro admin účet
admin_user = User.objects.get(username='admin')
admin_user.set_password('admin123')
admin_user.save()

print("✅ Admin heslo nastaveno na: admin123")
print("✅ Username: admin")
print("✅ Email: admin@example.com")