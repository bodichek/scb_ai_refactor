import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["GET"])
def get_company_data(request):
    """API endpoint pro načítání firemních údajů z IČO"""
    
    ico = request.GET.get('ico', '').strip()
    
    if not ico:
        return JsonResponse({
            "error": "IČO je povinné"
        }, status=400)
    
    # Validace IČO formátu
    if not ico.isdigit() or len(ico) != 8:
        return JsonResponse({
            "error": "IČO musí obsahovat přesně 8 číslic"
        }, status=400)
    
    try:
        # Volání API ARES (Administrativní registr ekonomických subjektů)
        ares_url = f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
        
        headers = {
            'User-Agent': 'FinApp/1.0 (https://finapp.cz)',
            'Accept': 'application/json'
        }
        
        print(f"DEBUG: Calling ARES URL: {ares_url}")
        response = requests.get(ares_url, headers=headers, timeout=10)
        print(f"DEBUG: Response status: {response.status_code}")
        
        if response.status_code == 404:
            return JsonResponse({
                "error": "Firma s tímto IČO nebyla nalezena v registru ARES"
            }, status=404)
        
        if response.status_code != 200:
            return JsonResponse({
                "error": f"Chyba při volání ARES API: {response.status_code}"
            }, status=500)
        
        data = response.json()
        
        # Debug výstup struktury dat
        print(f"DEBUG: ARES data structure: {data.keys()}")
        
        # Extrakce dat z ARES odpovědi
        company_data = {}
        
        # Základní údaje
        if 'obchodniJmeno' in data:
            company_data['company_name'] = data['obchodniJmeno']
        elif 'nazev' in data:
            company_data['company_name'] = data['nazev']
        
        # Adresa
        if 'sidlo' in data:
            sidlo = data['sidlo']
            address_parts = []
            
            # Sestavení adresy: Ulice číslo, Město PSČ
            if 'nazevUlice' in sidlo and sidlo['nazevUlice']:
                street = str(sidlo['nazevUlice'])
                if 'cisloDomovni' in sidlo and sidlo['cisloDomovni']:
                    street += f" {sidlo['cisloDomovni']}"
                address_parts.append(street)
            elif 'cisloDomovni' in sidlo and sidlo['cisloDomovni']:
                address_parts.append(f"č.p. {sidlo['cisloDomovni']}")
                
            if 'nazevObce' in sidlo and sidlo['nazevObce']:
                city_part = str(sidlo['nazevObce'])
                if 'psc' in sidlo and sidlo['psc']:
                    city_part = f"{sidlo['psc']} {city_part}"
                address_parts.append(city_part)
                
            company_data['address'] = ', '.join(address_parts)
            company_data['city'] = str(sidlo.get('nazevObce', '')) if sidlo.get('nazevObce') else ''
            company_data['postal_code'] = str(sidlo.get('psc', '')) if sidlo.get('psc') else ''
        
        # Právní forma
        if 'pravniForma' in data and data['pravniForma']:
            pravni_forma = data['pravniForma']
            if isinstance(pravni_forma, dict):
                company_data['legal_form'] = pravni_forma.get('nazev', '')
            else:
                company_data['legal_form'] = str(pravni_forma)
        
        # Činnosti (odvětví)
        if 'cinnosti' in data and data['cinnosti'] and isinstance(data['cinnosti'], list):
            # Vezmi první hlavní činnost
            hlavni_cinnost = None
            for cinnost in data['cinnosti']:
                if isinstance(cinnost, dict):
                    if cinnost.get('hlavni', False):
                        hlavni_cinnost = cinnost.get('nazev', '')
                        break
            
            if not hlavni_cinnost and data['cinnosti']:
                first_cinnost = data['cinnosti'][0]
                if isinstance(first_cinnost, dict):
                    hlavni_cinnost = first_cinnost.get('nazev', '')
                else:
                    hlavni_cinnost = str(first_cinnost)
            
            company_data['industry'] = hlavni_cinnost or ''
        
        # Stav subjektu
        company_data['active'] = data.get('stavZaznamu', '') == 'AKTIVNI'
        
        return JsonResponse({
            "success": True,
            "data": company_data,
            "source": "ARES"
        })
        
    except requests.RequestException as e:
        return JsonResponse({
            "error": f"Chyba při komunikaci s ARES: {str(e)}"
        }, status=500)
    except json.JSONDecodeError:
        return JsonResponse({
            "error": "Chyba při zpracování odpovědi z ARES"
        }, status=500)
    except Exception as e:
        return JsonResponse({
            "error": f"Neočekávaná chyba: {str(e)}"
        }, status=500)