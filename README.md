## Road to Ban tout l'extrême droite sur Instagram

Pas mal de posts instagram ont commencé à partager des listes de comptes d'extrême droite à bloquer.

https://www.instagram.com/p/DfCaZQxCIPr/?utm_source=ig_web_copy_link&exln=MzRlODBiNWFlZA==&srtk=MzRlODBiNWFlZA==

L'idée de ce projet est de faciliter le blocage de ces comptes en automatisant le processus sur Instagram. Je trouvais ça assez fastidieux de le faire manuellement pour chaque compte, donc ce script permet de gagner du temps et d'assurer que les comptes soient bien bloqués. Surtout qu'Instagram peut parfois débloquer des comptes que vous aviez bloqués de manière périodique.

Le script est écrit en Python et utilise [Playwright](https://playwright.dev/) pour automatiser les interactions avec Instagram. `comptes.txt` contient la liste des comptes à bloquer, un par ligne. Le script se charge ensuite de les bloquer automatiquement en suivant les étapes nécessaires sur Instagram. Pour l'instant, j'ai chargé les comptes depuis des listes partagées sur Instagram, mais vous pouvez ajouter vos propres comptes à bloquer dans `comptes.txt`. Vous pouvez aussi proposer des modifications ou des ajouts au projet si vous le souhaitez.

### Installation

1. Assurez-vous d'avoir Python installé sur votre machine.
2. Installez les dépendances nécessaires avec la commande :
   ```bash
   pip install playwright
   python -m playwright install chromium
   ```
3. Lancez le script avec :
   ```bash
   python block-accounts.py
   ```

Une fenêtre de navigateur s'ouvrira automatiquement. Vous devrez vous connecter à votre compte Instagram puis le script se chargera de bloquer les comptes listés dans `comptes.txt`.

L'exécution est assez lente, pour qu'Instagram ne bloque pas votre compte pour activité suspecte, il est recommandé de ne pas bloquer trop de comptes d'un coup. Vous pouvez exécuter le script plusieurs fois avec des listes plus petites si nécessaire.
