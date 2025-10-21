from pyngrok import ngrok

# 🔑 tvůj ngrok token z dashboardu
ngrok.set_auth_token("33EVHZnzx5n5pGbKBYrByZ5rJjJ_4utGYwyWkgM426EJ4GA6z")

# 🚀 spustí tunel na port 8000
public_url = ngrok.connect(8000)
print("🚀 Veřejná adresa:", public_url)
print("✅ Tunel běží – nech toto okno otevřené, dokud testuješ aplikaci.")
input("Stiskni Enter pro ukončení...")
