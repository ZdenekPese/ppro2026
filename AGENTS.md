# Pokyny pro AI agenty (AGENTS.md)
> **Projekt:** Sklad pro malý e-shop (*Dřevěnka s.r.o.*)  
> **Předmět:** Pokročilé programování (PPRO), ZS 2026/2027, FIM UHK  
> **Jediný zdroj pravdy (SSOT):** [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md)

Tento soubor definuje závazná provozní pravidla, architektonické mantinely a postupy pro všechny AI agenty a asistenty pracující v tomto repozitáři.

---

## 🛑 1. Zlatá pravidla (Kritická omezení)

### Pravidlo A: Zákaz svévolného Git Push
- **NIKDY neprovádějte příkaz `git push`** automaticky, na pozadí ani z vlastního uvážení.
- Operace `git push` je striktně podmíněna **výslovným a přímým povelem uživatele** v chatu (např. *„pushni změny“*, *„můžeš provést push“*).

### Pravidlo B: README.md jako Jediný zdroj pravdy (SSOT)
- Veškeré požadavky klienta, technická rozhodnutí (ADR), datové modely, popis rozhraní a deník postupu (Changelog) se evidují přímo v [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md).
- Žádná architektonická či funkční změna nesmí být provedena v kódu bez současné aktualizace dokumentace v [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md).

### Pravidlo C: Předcommitová disciplína (Pre-commit)
- V repozitáři je aktivní hook `.git/hooks/pre-commit`.
- Před každým `git commit` musí být zkontrolováno, že [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md) zachycuje provedené změny a je přidán do stage (`git add README.md`).

---

## 🏛️ 2. Technické a architektonické standardy (PPRO)

Všechny implementační kroky musí respektovat povinné minimum předmětu PPRO:

1. **Tři vrstvy se závislostmi jedním směrem:**
   - **Prezentační vrstva:** REST API / Web UI. Závisí pouze na aplikační/byznys vrstvě.
   - **Aplikační a doménová vrstva:** Byznys služby, validace doménových invariantů, transakční hranice. Nezávisí na prezentační vrstvě.
   - **Persistenční / Infrastrukturní vrstva:** Databázový kontext, repozitáře, migrace, integrace externích služeb.
2. **Relační databáze v Dockeru s migracemi:**
   - Databáze PostgreSQL běžící v Docker kontejneru.
   - Schéma je spravováno výhradně verzovanými migracemi.
3. **Doménový model:**
   - Minimálně 5 entit (projekt jich specifikuje 8: `Product`, `Category`, `ProductCategory`, `Warehouse`, `WarehouseStock`, `StockMovement`, `Customer`, `Order`, `OrderItem`).
   - Minimálně jedna vazba M:N (`Product` $\leftrightarrow$ `Category` přes `ProductCategory`).
4. **Spustitelnost:**
   - Celý stack (databáze + migrace + aplikace) musí být spustitelný jedním příkazem `docker compose up --build`.
5. **Data a bezpečnost:**
   - Pouze syntetická data. Žádné reálné osobní údaje, žádná tajemství ani hesla v gitu.

---

## 💼 3. Klíčová byznys pravidla domény (Zadání B)

Při psaní kódu a testů striktně vynucujte tato pravidla:

1. **Zákaz záporného stavu zásob (`quantity >= 0`):**
   - Vydat víc, než je skladem, nesmí projít ani omylem.
   - Rozpory mezi evidencí a realitou se řeší přes modul *Inventura / Vyrovnání* s plnou auditní stopou.
2. **Dvoufázový stav zásob (Fyzická vs. Disponibilní zásoba):**
   - $\text{Disponibilní} = \text{Fyzická} - \text{Rezervovaná}$.
   - Při přijetí objednávky: okamžitá **rezervace** (zamezí přeprodeji).
   - Při expedici: **fyzický odpis** a uvolnění rezervace s vytvořením záznamu o pohybu (`StockMovement`).
3. **Neměnnost ceny v objednávce:**
   - Položka objednávky (`OrderItem`) má fixovanou prodejní cenu v čase vytvoření. Pozdější změna ceníku produktu se do ní nepromítá.
4. **Zákaz mazání zákazníků:**
   - Záznamy v tabulce zákazníků se fyzicky nemažou (historie reklamací).
5. **Dohledatelnost všech pohybů (Audit log):**
   - Každá změna skladové zásoby vyžaduje záznam v `StockMovement` (typ: příjem, výdej, meziskladový přesun, inventurní korekce).
6. **Řízení skladů (Hradec Králové vs. Garáž Třebechovice):**
   - Expedice probíhá centrálně z Hradce.
   - Nedostatek v Hradci řeší meziskladový transfer z garáže v Třebechovicích, nikoliv rozdělení balíku zákazníkovi na dvě zásilky.

---

## 🛠️ 4. Pokyny pro provádění změn

Při řešení každého úkolu postupujte podle tohoto cyklu:
1. **Analýza:** Ověřte v [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md) aktuální stav, existující rozhodnutí a konvence.
2. **Implementace:** Proveďte změny v kódu, testech nebo konfiguraci.
3. **Testování:** Ověřte funkčnost a spusťte testy.
4. **Aktualizace SSOT:** Zapište změny, nová rozhodnutí a aktualizujte sekci *Changelog* v [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md).
5. **Commit:** Přidejte změněné soubory i `README.md` do Gitu a proveďte commit.
6. **Report uživateli:** Stručně shrňte výsledek a v případě potřeby pushnutí požádejte o schválení.
