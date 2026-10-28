import csv
import math
import random
import re
import time
from datetime import datetime, date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------- Configuration ----------------
FICHIERS_COMPTES = ["comptes.txt", "comptes_perso.txt"]
FICHIER_RESULTATS = "resultats.csv"
DOSSIER_SESSION = "./ig_session"
DELAI_MIN, DELAI_MAX = 8, 20     # secondes entre deux comptes
MAX_PAR_JOUR = 30                # blocages effectifs maximum par jour
REVERIF_JOURS = 30               # revérifier un compte bloqué au bout de N jours
HEADLESS = False
# ------------------------------------------------

STATUTS_OK = ("bloqué", "déjà bloqué", "introuvable")

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
    for fichier in FICHIERS_COMPTES:
        chemin = Path(fichier)
        if not chemin.exists():
            continue
        for l in chemin.read_text(encoding="utf-8").splitlines():
            u = normaliser(l)
            if u and u not in comptes:
                comptes.append(u)
    return comptes


def lire_historique() -> tuple[dict[str, datetime], int]:
    """Renvoie la date de dernière confirmation de chaque compte
    et le nombre de blocages effectués aujourd'hui."""
    historique: dict[str, datetime] = {}
    bloques_aujourdhui = 0
    if not Path(FICHIER_RESULTATS).exists():
        return historique, 0

    with open(FICHIER_RESULTATS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = datetime.fromisoformat(r["date"])
            if r["statut"] in STATUTS_OK:
                historique[r["compte"]] = d
            if r["statut"] == "bloqué" and d.date() == date.today():
                bloques_aujourdhui += 1
    return historique, bloques_aujourdhui


def comptes_a_traiter(comptes: list[str], historique: dict[str, datetime]) -> list[str]:
    """Priorité aux comptes jamais traités, puis à ceux à revérifier."""
    limite = datetime.now() - timedelta(days=REVERIF_JOURS)
    jamais = [c for c in comptes if c not in historique]
    a_reverifier = [c for c in comptes if c in historique and historique[c] < limite]
    return jamais + a_reverifier


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
    tous = charger_comptes()
    historique, bloques_aujourdhui = lire_historique()
    file_attente = comptes_a_traiter(tous, historique)
    quota = MAX_PAR_JOUR - bloques_aujourdhui

    faits = sum(1 for c in tous if c in historique)
    print(f"📊 Avancement : {faits}/{len(tous)} comptes traités")
    print(f"   Aujourd'hui : {bloques_aujourdhui}/{MAX_PAR_JOUR} blocages")

    if not file_attente:
        print("✅ Tous les comptes sont à jour. Rien à faire.")
        return
    if quota <= 0:
        print("⏸️  Quota du jour atteint. Relancez demain.")
        return

    print(f"   À traiter : {len(file_attente)} compte(s), quota restant : {quota}\n")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            DOSSIER_SESSION,
            channel="chrome",
            headless=HEADLESS,
            locale="fr-FR",
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        try:
            verifier_connexion(page)

            bloques_session = 0
            for compte in file_attente:
                if bloques_session >= quota:
                    print("\n⏸️  Quota du jour atteint.")
                    break

                print(f"\n@{compte}")
                try:
                    statut, detail = bloquer(page, compte)
                except PWTimeout:
                    statut, detail = "erreur", "timeout"
                    page.screenshot(path=f"erreur_{compte}.png")
                except Exception as e:
                    statut, detail = "erreur", str(e)[:150]
                    page.screenshot(path=f"erreur_{compte}.png")
                log_resultat(compte, statut, detail)

                if statut == "bloqué":
                    bloques_session += 1

                if "Réessayez plus tard" in page.content() or "Try Again Later" in page.content():
                    print("⚠️ Instagram limite les actions. Arrêt, réessayez demain.")
                    break

                time.sleep(random.uniform(DELAI_MIN, DELAI_MAX))
        finally:
            # Fermeture propre pour que la session soit bien sauvegardée,
            # même en cas d'interruption (Ctrl+C) ou d'erreur
            ctx.close()

    # Estimation du temps restant
    historique, _ = lire_historique()
    restants = len(comptes_a_traiter(tous, historique))
    if restants:
        jours = math.ceil(restants / MAX_PAR_JOUR)
        print(f"\n📅 Encore {restants} compte(s), environ {jours} jour(s). Relancez demain.")
    else:
        print("\n🎉 Tous les comptes sont bloqués !")


if __name__ == "__main__":
    main()