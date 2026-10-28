## Road to Ban toute l'extrême droite sur Instagram

Pas mal de posts Instagram ont commencé à partager des listes de comptes d'extrême droite à bloquer.

https://www.instagram.com/p/DfCaZQxCIPr/

L'idée de ce projet est de faciliter le blocage de ces comptes en automatisant le processus sur Instagram. Je trouvais assez fastidieux de le faire manuellement pour chaque compte. Ce script permet de gagner du temps et de s'assurer que les comptes restent bien bloqués, d'autant qu'Instagram débloque parfois périodiquement des comptes que vous aviez bloqués.

Le script est écrit en Python et utilise [Playwright](https://playwright.dev/) pour automatiser les interactions avec Instagram. Le fichier `comptes.txt` contient la liste des comptes à bloquer, un par ligne. Elle provient de listes partagées sur Instagram et du site [onbloquelextremedroite.fr](https://www.onbloquelextremedroite.fr/liste). Vous pouvez aussi ajouter vos propres comptes (voir plus bas). N'hésitez pas à proposer des modifications ou des ajouts au projet.

### Installation

1. Assurez-vous d'avoir [Python](https://www.python.org/downloads/) installé sur votre machine.
2. Installez [Google Chrome](https://www.google.com/chrome/) s'il n'est pas déjà présent.
3. Clonez le dépôt et installez Playwright :
   ```bash
   git clone https://github.com/paulcharles2701-beep/ban-extreme-droite-instagram
   cd ban-extreme-droite-instagram
   pip install playwright
   ```

### Utilisation

1. Récupérez la dernière version de la liste :
   ```bash
   git pull
   ```

2. Lancez le blocage :
   ```bash
   python block-accounts.py
   ```

Une fenêtre Chrome s'ouvre. Au premier lancement, connectez-vous à votre compte Instagram, puis appuyez sur Entrée dans le terminal. La session est ensuite mémorisée : vous n'aurez plus à vous reconnecter lors des exécutions suivantes.

⏱️ **Une exécution dure environ 10 minutes.** Le script marque volontairement des pauses entre chaque compte pour imiter un comportement humain. Vous pouvez laisser la fenêtre ouverte en arrière-plan, mais ne la fermez pas pendant l'exécution.

### Une liste mise à jour automatiquement

La liste `comptes.txt` est **mise à jour automatiquement toutes les 24 heures, à 00h** (heure de Paris), grâce à une GitHub Action. Celle-ci récupère les comptes publiés sur [onbloquelextremedroite.fr](https://www.onbloquelextremedroite.fr/liste) et committe la nouvelle liste si elle a changé.

Pour en profiter, faites simplement un `git pull` avant de lancer le script. Les nouveaux comptes seront bloqués lors de l'exécution, et ceux déjà bloqués ne seront pas retraités.

### Ajouter vos propres comptes

Ne modifiez pas `comptes.txt` : il est réécrit à chaque mise à jour automatique. Créez plutôt un fichier `comptes_perso.txt` à la racine du projet, avec un compte par ligne :

```
@un_compte
https://www.instagram.com/un_autre_compte/
```

Ce fichier est lu en plus de la liste commune, et il est ignoré par Git : il reste sur votre machine.

### Un blocage réparti sur plusieurs jours

Bloquer beaucoup de comptes d'un coup peut amener Instagram à considérer votre activité comme suspecte, et à restreindre temporairement votre compte. Le script limite donc le nombre de blocages à **30 par jour** (paramètre `MAX_PAR_JOUR`). La liste actuelle d'environ 110 comptes est ainsi traitée en **4 jours**, à raison d'environ 10 minutes par jour.

Il suffit de **relancer le script une fois par jour** :

- l'avancement est enregistré dans `resultats.csv` ;
- les comptes déjà bloqués sont ignorés et le script reprend là où il s'est arrêté ;
- si le quota du jour est atteint, le script s'arrête et vous invite à revenir le lendemain ;
- à la fin de chaque exécution, il affiche le nombre de comptes restants et une estimation du nombre de jours nécessaires.

Exemple de sortie :

```
📊 Avancement : 30/109 comptes traités
   Aujourd'hui : 0/30 blocages
   À traiter : 79 compte(s), quota restant : 30
...
📅 Encore 49 compte(s), environ 2 jour(s). Relancez demain.
```

### Revérification automatique

Comme Instagram débloque parfois des comptes, chaque compte est **revérifié 30 jours** après son dernier contrôle (paramètre `REVERIF_JOURS`). S'il est toujours bloqué, rien ne se passe. Sinon, il est bloqué à nouveau. Une fois la liste entièrement traitée, lancer le script de temps en temps suffit pour garder vos blocages à jour.

### Paramètres

Les paramètres se trouvent en haut de `block-accounts.py` :

| Paramètre | Défaut | Description |
|---|---|---|
| `MAX_PAR_JOUR` | `30` | Nombre maximum de blocages par jour |
| `REVERIF_JOURS` | `30` | Délai avant de revérifier un compte déjà bloqué |
| `DELAI_MIN` / `DELAI_MAX` | `8` / `20` | Pause aléatoire entre deux comptes, en secondes |

Il est déconseillé d'augmenter fortement `MAX_PAR_JOUR` ou de réduire les délais.

### Fichiers du projet

| Fichier | Rôle |
|---|---|
| `block-accounts.py` | Script de blocage |
| `extraire_liste.py` | Extraction des comptes depuis le site (lancé automatiquement chaque nuit) |
| `comptes.txt` | Liste commune, mise à jour automatiquement |
| `comptes.json` | Liste commune avec les détails (nom, catégorie, photo…) |
| `comptes_perso.txt` | Vos comptes personnels *(à créer, non versionné)* |
| `resultats.csv` | Historique de vos blocages *(généré, non versionné)* |
| `ig_session/` | Votre session Instagram *(générée, non versionnée)* |

### En cas de problème

- **« Réessayez plus tard »** : Instagram limite temporairement vos actions. Le script s'arrête de lui-même. Attendez au moins 24 h avant de relancer.
- **Un compte en erreur** : une capture d'écran `erreur_<compte>.png` est créée. Le compte sera retenté au prochain lancement.
- **Problème de connexion** : supprimez le dossier `ig_session/` et relancez le script pour vous reconnecter.
- **Recommencer de zéro** : supprimez `resultats.csv`.

### Pour les contributeurs

La mise à jour de la liste est gérée par le workflow `.github/workflows/maj-liste.yml`. Il peut être lancé manuellement depuis l'onglet *Actions* du dépôt (*Run workflow*). Pour mettre à jour la liste en local :

```bash
python -m playwright install chromium
python extraire_liste.py
```