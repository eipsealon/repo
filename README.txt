APT-репозиторий для GitHub Pages (Sileo/Zebra/Cydia).

1. Отредактируйте REPO_NAME, REPO_DESC, REPO_URL в build_repo.py.
2. Положите .deb в debs/ и выполните ./update.sh
3. Создайте ПУБЛИЧНЫЙ репозиторий на GitHub и запушьте всё содержимое папки:
     git init -b main && git add . && git commit -m repo
     git remote add origin https://github.com/ИМЯ/РЕПО.git
     git push -u origin main
4. GitHub -> Settings -> Pages -> Source: Deploy from a branch -> main, папка / (root)
5. Через 1-2 минуты репозиторий доступен: https://ИМЯ.github.io/РЕПО/
6. На телефоне: Sileo -> Источники -> + -> вставьте этот URL.

Обновление: новый .deb в debs/ (можно удалить старые версии), ./update.sh, git add -A, git commit, git push.
