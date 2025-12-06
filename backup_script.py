import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.core import management

apps = [
    'auth',
    'accounts',
    'survey',
    'suropen',
    'chatbot',
    'coaching',
    'intercom',
    'ingest',
    'exports'
]

print("Starting backup...")

for app in apps:
    try:
        filename = f'backup_{app}.json'
        print(f"Exporting {app}...")
        with open(filename, 'w', encoding='utf-8') as f:
            management.call_command(
                'dumpdata',
                app,
                stdout=f,
                natural_foreign=True,
                natural_primary=True,
                indent=2
            )
        print(f"OK {app} exported to {filename}")
    except Exception as e:
        print(f"ERROR exporting {app}: {e}")

print("\nBackup completed!")
