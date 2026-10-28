import csv
import random
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------- Configuration ----------------
FICHIER_COMPTES = "comptes.txt"
FICHIER_RESULTATS = "resultats.csv"
DOSSIER_SESSION = "./ig_session"     # profil navigateur persistant
DELAI_MIN, DELAI_MAX = 8, 20          # secondes entre deux comptes
MAX_PAR_SESSION = 40                  # éviter de dépasser les limites d'Instagram
HEADLESS = False                      # garder False pour la première connexion
# ------------------------------------------------

# Regex FR + EN pour être robuste à la langue de l'interface
RE_BLOQUER = re.compile(r"^(Bloquer|Block)$", re.I)
RE_DEBLOQUER = re.compile(r"^(Débloquer|Unblock)$", re.I)
RE_FERMER = re.compile(r"^(Fermer|Ignorer|Dismiss|Close|OK)$", re.I)


def normaliser(ligne: str) -> str | None:
    ligne = ligne.strip()
    if not ligne or ligne.startswith("#"):
        return None
    m = re.search(r"instagram\.com/([^/?#]+)", ligne)
    if m:
        ligne = m.group(1)
    return ligne.lstrip("@").strip("/").lower()


def charger_comptes() -> list[str]:
    comptes = []
    for l in Path(FICHIER_COMPTES).read_text(encoding="utf-8").splitlines():
        u = normaliser(l)
        if u and u not in comptes:
            comptes.append(u)
    return comptes


def deja_traites() -> set[str]:
    """Permet de reprendre là où on s'est arrêté."""
    if not Path(FICHIER_RESULTATS).exists():
        return set()
    with open(FICHIER_RESULTATS, encoding="utf-8") as f:
        return {r["compte"] for r in csv.DictReader(f)
                if r["statut"] in ("bloqué", "déjà bloqué", "introuvable")}


def log_resultat(compte: str, statut: str, detail: str = ""):
    nouveau = not Path(FICHIER_RESULTATS).exists()
    with open(FICHIER_RESULTATS, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nouveau:
            w.writerow(["date", "compte", "statut", "detail"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), compte, statut, detail])
    print(f"[{statut}] @{compte} {detail}")


def pause(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))


def est_connecte(ctx) -> bool:
    cookies = ctx.cookies("https://www.instagram.com")
    return any(c["name"] == "sessionid" and c["value"] for c in cookies)


def verifier_connexion(page, timeout_min: int = 5):
    ctx = page.context
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")

    if est_connecte(ctx):
        print("Déjà connecté.")
        return

    print(f"Connectez-vous dans la fenêtre du navigateur "
          f"(vous avez {timeout_min} min, double authentification comprise)...")

    limite = time.time() + timeout_min * 60
    while time.time() < limite:
        if est_connecte(ctx):
            print("Connexion détectée.")
            # Laisse passer les écrans "Enregistrer vos identifiants ?" / notifications
            pause(4, 6)
            return
        time.sleep(2)

    raise SystemExit("Délai dépassé : connexion non détectée. Relancez le script.")


def bloquer(page, compte: str) -> tuple[str, str]:
    page.goto(f"https://www.instagram.com/{compte}/", wait_until="domcontentloaded")
    pause(3, 5)

    # Compte inexistant
    contenu = page.content()
    if ("Cette page n’est pas disponible" in contenu
            or "Sorry, this page isn't available" in contenu
            or "Profile isn't available" in contenu):
        return "introuvable", ""

    # Déjà bloqué : le profil affiche un bouton "Débloquer"
    if page.get_by_role("button", name=RE_DEBLOQUER).count():
        return "déjà bloqué", ""

    # 1) Bouton "Options" (les trois points) sur le profil
    options = page.locator("svg[aria-label='Options']").first
    options.wait_for(timeout=10_000)
    options.click()
    pause()

    # 2) "Bloquer" dans le menu
    dialog = page.get_by_role("dialog").last
    dialog.get_by_role("button", name=RE_BLOQUER).first.click()
    pause()

    # 3) Confirmation : bouton "Bloquer" dans la nouvelle boîte de dialogue
    confirm = page.get_by_role("dialog").last
    confirm.get_by_role("button", name=RE_BLOQUER).last.click()
    pause(2, 3)

    # 4) Fermer l'éventuelle fenêtre "Vous avez bloqué..."
    try:
        page.get_by_role("button", name=RE_FERMER).first.click(timeout=4_000)
    except PWTimeout:
        pass

    # Vérification
    page.reload(wait_until="domcontentloaded")
    pause(2, 4)
    if page.get_by_role("button", name=RE_DEBLOQUER).count():
        return "bloqué", ""
    return "incertain", "bouton Débloquer non détecté après l'action"


def main():
    comptes = [c for c in charger_comptes() if c not in deja_traites()]
    print(f"{len(comptes)} compte(s) à traiter.")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            DOSSIER_SESSION,
            channel="chrome",
            headless=False,
            locale="fr-FR",
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        verifier_connexion(page)

        for i, compte in enumerate(comptes[:MAX_PAR_SESSION], 1):
            print(f"\n({i}/{min(len(comptes), MAX_PAR_SESSION)}) @{compte}")
            try:
                statut, detail = bloquer(page, compte)
            except PWTimeout as e:
                statut, detail = "erreur", "timeout"
                page.screenshot(path=f"erreur_{compte}.png")
            except Exception as e:
                statut, detail = "erreur", str(e)[:150]
                page.screenshot(path=f"erreur_{compte}.png")
            log_resultat(compte, statut, detail)

            # Si Instagram signale une limitation, on s'arrête
            if "Réessayez plus tard" in page.content() or "Try Again Later" in page.content():
                print("Instagram limite les actions. Arrêt — réessayez dans quelques heures.")
                break

            time.sleep(random.uniform(DELAI_MIN, DELAI_MAX))

        ctx.close()


if __name__ == "__main__":
    main()