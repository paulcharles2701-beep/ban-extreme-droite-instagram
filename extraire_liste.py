import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://www.onbloquelextremedroite.fr/liste"
FICHIER_TXT = "comptes.txt"
FICHIER_JSON = "comptes.json"

# Catégories à garder (vide = toutes). Ex : {"Partis politiques", "Médias"}
CATEGORIES_INCLUSES: set[str] = set()


def nettoyer_handle(handle: str | None, url: str | None) -> str | None:
    """Renvoie un identifiant propre, sans @ ni espaces."""
    if handle:
        h = handle.strip().lstrip("@").strip()
        if h:
            return h.lower()
    # Repli : on extrait l'identifiant depuis l'URL du profil
    if url:
        m = re.search(r"instagram\.com/([^/?#]+)", url)
        if m:
            return m.group(1).lower()
    return None


def extraire(page) -> list[dict]:
    """Extrait tous les comptes de toutes les sections, en une seule évaluation JS."""
    return page.evaluate(
        """
        () => {
          const txt = (el) => el ? el.textContent.trim() : null;
          const resultats = [];

          document.querySelectorAll("section[aria-label]").forEach((section) => {
            const categorie = section.getAttribute("aria-label");
            const titre = txt(section.querySelector(".section-head h2"));
            const annonce = txt(section.querySelector(".section-head p"));

            section.querySelectorAll(".accounts article.account").forEach((art) => {
              const report = art.querySelector("button.report");
              resultats.push({
                categorie,
                titre_categorie: titre,
                nombre_annonce: annonce,
                nom: txt(art.querySelector(".account-identity .name")),
                handle: txt(art.querySelector(".account-identity .handle")),
                url: art.querySelector("a.open")?.getAttribute("href") ?? null,
                photo: art.querySelector(".profile-photo")?.getAttribute("src") ?? null,
                report_handle: report?.dataset.handle ?? null,
                plateforme: report?.dataset.platform ?? null,
              });
            });
          });
          return resultats;
        }
        """
    )


def est_instagram(compte: dict) -> bool:
    plateforme = (compte.get("plateforme") or "").lower()
    url = (compte.get("url") or "").lower()
    return plateforme == "instagram" or "instagram.com" in url


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="fr-FR")
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector("article.account", timeout=15_000)
        bruts = extraire(page)
        browser.close()

    if not bruts:
        sys.exit("Aucun compte trouvé : la structure de la page a peut-être changé.")

    # Nettoyage, filtrage Instagram, regroupement par catégorie, dédoublonnage
    par_categorie: dict[str, list[dict]] = {}
    vus: set[str] = set()

    for c in bruts:
        if not est_instagram(c):
            continue
        if CATEGORIES_INCLUSES and c["categorie"] not in CATEGORIES_INCLUSES:
            continue
        handle = nettoyer_handle(c["handle"] or c["report_handle"], c["url"])
        if not handle or handle in vus:
            continue
        vus.add(handle)
        c["handle"] = handle
        par_categorie.setdefault(c["categorie"], []).append(c)

    # Fichier texte : une ligne par compte, catégories en commentaire
    # (les lignes commençant par # sont ignorées par le script de blocage)
    lignes = []
    for categorie, comptes in par_categorie.items():
        lignes.append(f"# {categorie} ({len(comptes)})")
        lignes += [f"@{c['handle']}" for c in comptes]
        lignes.append("")
    Path(FICHIER_TXT).write_text("\n".join(lignes), encoding="utf-8")

    # Fichier JSON : toutes les métadonnées, regroupées par catégorie
    Path(FICHIER_JSON).write_text(
        json.dumps(par_categorie, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Récapitulatif avec contrôle du nombre annoncé
    print(f"{len(vus)} comptes Instagram extraits\n")
    for categorie, comptes in par_categorie.items():
        annonce = comptes[0].get("nombre_annonce") or "?"
        print(f"  {categorie:<40} {len(comptes):>4} extraits  (annoncé : {annonce})")
    print(f"\n→ {FICHIER_TXT}\n→ {FICHIER_JSON}")


if __name__ == "__main__":
    main()