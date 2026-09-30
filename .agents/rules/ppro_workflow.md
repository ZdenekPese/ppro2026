# Zásady projektu PPRO (Sklad pro malý e-shop - Dřevěnka s.r.o.)

Tyto zásady jsou závazné pro všechny úkoly a interakce v tomto repozitáři:

## 1. Pravidlo pro operaci Git Push
- **NIKDY neprovádět `git push` automaticky ani svévolně.**
- Operace `git push` je povolena **výhradně po explicitním příkazu uživatele** v chatu (např. „můžeš pushnout“, „pushni změny“, „proveď git push“).

## 2. README.md jako Jediný zdroj pravdy (SSOT)
- [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md) slouží jako technická dokumentace, kompletní zadání, záznam architektonických i funkčních rozhodnutí (ADR) a deník postupu projektu.
- Jakákoliv změna architektury, datového modelu, byznys logiky nebo stavu implementace **musí být okamžitě promítnuta do README.md**.

## 3. Předcommmitová disciplína (Pre-commit)
- Před každým commitem musí být zkontrolováno, že [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md) je aktuální a zachycuje veškeré nově provedené změny, rozhodnutí a postup.
- [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md) musí být součástí commitu, pokud se mění kód nebo konfigurace.

## 4. Dodržování zadání a povinného minima PPRO
- Tři vrstvy se závislostmi jedním směrem (API/UI -> Aplikační/Byznys logika -> Datová vrstva).
- Relační databáze v Dockeru s migracemi.
- Nejméně 5 entit a minimálně jedna vazba M:N.
- Automatizované testy klíčových obchodních pravidel (zejména zákaz záporného stavu a výdeje nad zásoby, fixace ceny, audit pohybů).
- Celá aplikace spustitelná pomocí `docker compose up`.
- Výhradně syntetická data.
