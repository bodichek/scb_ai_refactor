#!/usr/bin/env python
"""
Test script pro ověření charts API endpointu
"""
import os
import sys
import django

# Nastavíme Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
import json

def test_charts_api():
    print("=== Test Charts API ===")
    
    # Získáme test uživatele
    client_user = User.objects.filter(username='brona.klus@gmail.com').first()  # Uživatel s finančními daty
    admin_user = User.objects.filter(username='admin').first()
    
    if not client_user:
        print("❌ brona.klus@gmail.com user nebyl nalezen")
        return
    
    if not admin_user:
        print("❌ admin user nebyl nalezen")
        return
        
    print(f"✅ Klient nalezen: {client_user.username} (ID: {client_user.id})")
    print(f"✅ Admin nalezen: {admin_user.username}")
    
    # Vytvoříme test client
    test_client = Client()
    test_client.force_login(admin_user)
    
    # Test API endpointu
    url = f'/coaching/client/{client_user.id}/charts-data/'
    print(f"🔍 Testujeme URL: {url}")
    
    try:
        response = test_client.get(url, follow=False)  # Nesleduj redirecty
        print(f"📊 HTTP Status: {response.status_code}")
        
        if response.status_code == 302:
            redirect_url = response.get('Location', 'Unknown')
            print(f"🔄 Redirect to: {redirect_url}")
            
        elif response.status_code == 200:
            data = response.json()
            html_content = data.get('html', '')
            print(f"📝 HTML délka: {len(html_content)} znaků")
            print(f"✅ Success: {data.get('success')}")
            
            # Ukážeme začátek HTML
            if len(html_content) > 500:
                print("📄 HTML začátek:")
                print(html_content[:500] + "...")
            else:
                print("📄 Celý HTML:")
                print(html_content)
                
        else:
            print(f"❌ Chyba: {response.status_code}")
            try:
                print("Response content:")
                print(response.content.decode())
            except:
                print("Could not decode response content")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        
    # Doplňující testy
    print("\n=== Doplňující info ===")
    print(f"Admin je coach: {admin_user.coach}")
    
    # Zkusíme i coach dashboard URL
    dashboard_url = '/coaching/my-clients/'
    dashboard_response = test_client.get(dashboard_url)
    print(f"Dashboard URL ({dashboard_url}): {dashboard_response.status_code}")
    
    if dashboard_response.status_code == 302:
        print(f"Dashboard redirect to: {dashboard_response.get('Location', 'Unknown')}")
    
    print("✅ Test dokončen")

if __name__ == '__main__':
    test_charts_api()