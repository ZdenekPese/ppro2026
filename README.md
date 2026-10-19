# Sklad pro malý e-shop (Dřevěnka s.r.o.)
> **Semestrální projekt z předmětu Pokročilé programování (PPRO)**  
> Fakulta informatiky a managementu, Univerzita Hradec Králové, ZS 2026/2027  
> **Jediný zdroj pravdy (Single Source of Truth – SSOT):** Technická dokumentace, kompletní zadání, seznam architektonických rozhodnutí a deník vývoje.

---

## 📋 Obsah
1. [Základní informace](#-základní-informace)
2. [Zásady a pravidla repozitáře](#-zásady-a-pravidla-repozitáře)
3. [Zadání klienta a analýza domény](#-zadání-klienta-a-analýza-domény)
4. [Povinné technické minimum projektu](#-povinné-technické-minimum-projektu)
5. [Rozhodnutí (Architecture Decision Records – ADR)](#-rozhodnutí-architecture-decision-records--adr)
6. [Datový model a doménové entity](#-datový-model-a-doménové-entity)
7. [Architektura a vrstvy systému](#-architektura-a-vrstvy-systému)
8. [Uživatelské rozhraní a ergonomie (UI/UX)](#-uživatelské-rozhraní-a-ergonomie-uiux)
9. [Instalace a spuštění](#-instalace-a-spuštění)
10. [Celkový fázový plán vývoje projektu (Roadmap)](#-celkový-fázový-plán-vývoje-projektu-roadmap)
11. [Implementační plán – Pilotní demo](#-implementační-plán--pilotní-demo-správa-entit-product)
12. [Deník postupu a historie změn (Changelog)](#-deník-postupu-a-historie-změn-changelog)

---

## 📌 Základní informace
- **Zadání:** B – Sklad pro malý e-shop
- **Klient:** Petr Doležal, jednatel *Dřevěnka s.r.o.* (zakázková výroba a prodej tradičních dřevěných hraček)
- **Vyučující / konzultant:** Dominik Palla (`dominik.palla@uhk.cz`)
- **Vzdálený repozitář:** `https://github.com/ZdenekPese/ppro2026.git`
- **Kde se návrh láme:** **Okamžik odečtení zásoby a dohledatelnost skladových pohybů**.

---

## ⚙️ Zásady a pravidla repozitáře

Tento repozitář podléhá striktním zásadám vývoje definovaným v zadání předmětu a v pravidlech projektu:

1. **Explicitní povel pro Git Push:**
   - Žádný nástroj ani agent **nesmí provést operaci `git push` bez výslovného a jednoznačného příkazu uživatele** v chatu.
2. **README.md jako Jediný zdroj pravdy (SSOT):**
   - Veškeré požadavky, architektonická a datová rozhodnutí, popis rozhraní a stav realizace jsou udržovány v tomto dokumentu.
   - Neexistuje oddělená nezaznamenaná dokumentace – kód a dokumentace se vyvíjejí ruku v ruce.
3. **Předcommitová kontrola (Git Pre-Commit Hook):**
   - Repozitář má nakonfigurovaný Git hook (verzovaný v `.githooks/pre-commit` a aktivní v lokálním `.git/hooks/pre-commit` s `core.hooksPath = .githooks`), který před každým commitem ověřuje, zda byly se změnami v kódu provedeny také patřičné záznamy v [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md).
4. **Respekt k roli klienta na cvičeních:**
   - Klient může v průběhu semestru upřesnit či změnit zadání. Návrh systému je koncipován modulárně, aby takové změny ustál bez nutnosti kompletního přepracování.
5. **Použití výhradně syntetických dat:**
   - V repozitáři ani v databázi nesmí být uložena žádná reálná osobní data, produkční hesla či tajné klíče.

---

## 📦 Zadání klienta a analýza domény

### Výchozí situace klienta
Firma *Dřevěnka s.r.o.* funguje 10 let. V posledních třech letech dynamicky roste objem prodejů přes e-shop. Aktuální stav:
- Evidence cca 400 skladových položek probíhá v jednom sdíleném souboru v MS Excel, který mají současně otevřený 3 pracovníci na různých počítačích.
- Společnost má **dva sklady**:
  1. **Hlavní sklad v Hradci Králové** – expedice většiny běžných objednávek.
  2. **Druhý sklad (garáž v Třebechovicích pod Orebem)** – odkládání sezónního zboží a nadnormativních zásob.
- Objednávky přicházejí z e-shopu do e-mailu a skladníci je ručně přepisují.
- **Kritický problém:** Přibližně 2× měsíčně se prodá zboží, které již fyzicky není na skladě. Klient musí volat zákazníkům a omlouvat se, což poškozuje reputaci firmy a způsobuje zbytečné ztráty času.

### 1. Co klient chce (Funkční požadavky – povinné)
1. **Produkty a kategorie:** Produkt má název, kód (SKU), popis, nákupní cenu a prodejní cenu. Kategorií je více a produkt může patřit do několika kategorií současně (např. tatáž káča je „pro batolata“ i „dárky do 500 Kč“ – vazba M:N).
2. **Zásoby po skladech:** U každého produktu musí být přehledně vidět, kolik kusů leží v Hradci a kolik v garáži v Třebechovicích.
3. **Objednávky zákazníků:** Objednávka obsahuje identifikaci zákazníka, datum vytvoření, aktuální stav a jednotlivé položky (objednané množství a prodejní cena v okamžiku prodeje).
4. **Odmítnutí objednávky při nedostatku zásob:** Systém nesmí dovolit přijmout či potvrdit objednávku na zboží, které není disponibilní (klíčový byznys cíl).
5. **Dohledání pohybu (Audit trail):** Ke každému výdeji, příjmu či převodu musí být jednoznačně evidováno, ze kterého skladu se vydalo/přijalo, kdy a proč („kde je ta káča, co jsem ji měl minulý týden“).
6. **Přesun mezi sklady:** Možnost evidovat převoz zboží ze zimní garáže v Třebechovicích do Hradce Králové a opačně.
7. **Minimální zásoba a doporučení doobjednání:** Seznam produktů, jejichž stav klesl pod definovanou minimální hladinu, viditelný přímo na úvodním panelu.
8. **Měsíční obrat po kategoriích:** Finanční přehled prodejů seskupený dle kategorií za vybraný měsíc pro vyhodnocení ziskovosti sortimentu.

### 2. Na čem klient trvá (Obchodní pravidla – vynucená aplikací)
- **Zákaz výdeje do záporu:** Vydat víc zboží, než je reálně na daném skladě, nesmí jít ani omylem, ani ručně.
- **Neměnnost ceny v objednávce:** Cena v již přijaté/odeslané objednávce se nesmí zpětně změnit, pokud dojde k plošné úpravě ceníku produktů.
- **Dohledatelnost každé změny stavu:** Každá změna skladové zásoby musí mít odpovídající záznam o pohybu (kdo, kdy, kolik, odkud, kam, z jakého důvodu).
- **Zákaz mazání zákazníků:** Zákaznické karty se nesmí fyzicky mazat z databáze z důvodu historie nákupů a řešení případných reklamací.

### 3. Co klient prohodí mimochodem (Přání a ergonomie)
- *„Poštovné řešit nemusíme, to počítá e-shop.“* -> Logiku výpočtu přepravného nerealizujeme ve skladovém jádře.
- *„Ať to jde používat i z mobilu, já jsem půlku dne ve skladu.“* -> Responzivní, ergonomické rozhraní použitelné na tabletu/telefonu přímo u regálu.
- *„Faktury zatím ne, ale jednou určitě.“* -> Datový model připravit tak, aby šla vazba na fakturaci jednoduše napojit.
- *„Nejradši bych to měl barevně, ať vidím, co hoří.“* -> Přehledný dashboard s barevnou indikací kriticky nízkých zásob (červená = pod minimem, oranžová = blízko limitu, zelená = v pořádku).

---

## 🎯 Povinné technické minimum projektu

| Požadavek ze zadání | Způsob splnění v projektu |
| :--- | :--- |
| **Tři vrstvy se závislostmi jedním směrem** | 1. Prezentační vrstva (REST API / UI)<br>2. Aplikační a doménová vrstva (Byznys logika, služby, validace)<br>3. Persistenční / Infrastrukturní vrstva (ORM, Migrace, DB) |
| **Relační databáze v Dockeru** | PostgreSQL běžící v kontejneru v rámci `docker-compose.yml` |
| **Databázové migrace** | Řízené migrace verzované v repozitáři (např. EF Core Migrations nebo Flyway/Prisma) |
| **Nejméně 5 entit** | Navrženo 8 klíčových entit (`Product`, `Category`, `ProductCategory`, `Warehouse`, `WarehouseStock`, `StockMovement`, `Customer`, `Order`, `OrderItem`) |
| **Alespoň jedna vazba M:N** | Vazba `Product` $\leftrightarrow$ `Category` přes asociační entitu `ProductCategory` (plus vazba položek objednávky `Order` $\leftrightarrow$ `Product` přes `OrderItem`) |
| **Automatizované testy** | Unit a integrační testy pro klíčová pravidla (zákaz záporného stavu, rezervace zásob, neměnnost cen, audit pohybů) |
| **Spuštění jedním příkazem** | Kompletní běh aplikace včetně databáze přes `docker compose up` |
| **Technická dokumentace** | Vedení [README.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/README.md) jako jediného zdroje pravdy (SSOT) |
| **Bezpečnost a data** | Žádné reálné osobní údaje, pouze syntetická demo data, hesla mimo VCS |

---

## 🧠 Rozhodnutí (Architecture Decision Records – ADR)

V souladu s pokyny zadání pro otevřené body klienta zde definujeme jednoznačná rozhodnutí.

### ADR 1: Objednávka ze dvou skladů naráz a poštovné
- **Zadání klienta:** Na dotaz odpovídá *„asi jo, ale to poštovné“* a dál to nerozvede.
- **Rozhodnutí:** Objednávka zákazníka se standardně expeduje z jednoho centrálního skladu (Hradec Králové). Pokud některé zboží v Hradci chybí, ale nachází se v Garáži v Třebechovicích, systém objednávku nezamítne, nýbrž automaticky vygeneruje požadavek na **vnitroskladový převoz (Transfer)** z Třebechovic do Hradce.
- **Zdůvodnění:** Odesílání dvou samostatných zásilek zákazníkovi by znamenalo dvojí poštovné a zmatení zákazníka. Převoz zboží mezi sklady odpovídá běžné praxi klienta a šetří náklady na dopravu.

### ADR 2: Co znamená „dost zásob“ a okamžik odečtení zásoby
- **Zadání klienta:** Není jasné, zda se počítá fyzický stav, nebo stav snížený o rezervace, a kdy se zásoba odečítá.
- **Rozhodnutí:** Zavádíme dvoustupňový model zásoby:
  $$\text{Disponibilní zásoba} = \text{Fyzická zásoba na skladě} - \text{Rezervováno v otevřených objednávkách}$$
  Při přijetí/vytvoření objednávky dochází k okamžité **rezervaci** disponibilní zásoby. K **fyzickému odpisu** (vyskladnění) dochází až při samotné expedici zboží a předání dopravci.
- **Zdůvodnění:** Okamžitá rezervace zabraňuje přeprodeji stejného zboží (splněn bod 4 zadání). Fyzický odpis při expedici odpovídá reálnému stavu polic ve skladu a umožňuje případné storno bez nutnosti složitých zpětných naskladnění.

### ADR 3: Záporný stav a inventurní nesrovnalosti
- **Zadání klienta:** V garáži stav *„nikdy nesedí“*. Neřekl, zda zápor zakázat, nebo umožnit inventuru.
- **Rozhodnutí:** Záporný stav zásob je v celém systému striktně **zakázán** na úrovni databázových i aplikačních integritních omezení (`quantity >= 0`). Nesrovnalosti v garáži i v Hradci se řeší modulem **Inventura / Vyrovnání skladu**, který umožní přepsat evidovaný stav na skutečný zjištěný počet a rozdíl (přebytek či manko) zaeviduje jako samostatný auditní pohyb se zdůvodněním.
- **Zdůvodnění:** Povolení záporných zásob deformuje výpočet ziskovosti, minimálních zásob i plánování nákupů. Inventurní záznam zachovává čisté účetnictví i dohledatelnost chyb.

### ADR 4: Varianty produktu (SKU vs. vlastnosti)
- **Zadání klienta:** Mluví o *„té samé káče ve třech barvách“*. Zda je to samostatný produkt, či vlastnost, nerozliší.
- **Rozhodnutí:** Každá varianta (např. červená káča, modrá káča) má svůj **vlastní unikátní kód (SKU)** a je samostatnou skladovou jednotkou s vlastní evidencí počtu kusů. Varianty jsou sdruženy pod společný rodičovský produkt a sdílejí popis a kategorie.
- **Zdůvodnění:** Skladník v regálu musí přesně vědět, kolik červených káč má na skladě; nelze mít skladem „3 káče obecně“, pokud zákazník očekává konkrétní barvu.

### ADR 5: Změna objednávky po zaplacení
- **Zadání klienta:** Stává se to a dnes se to řeší telefonem; co má systém dovolit, klient neví.
- **Rozhodnutí:** Dokud objednávka není fyzicky expedována, systém umožňuje její úpravu pověřenou osobou:
  - Odebrání položky okamžitě uvolní její rezervaci a vygeneruje přeplatek.
  - Přidání položky je dovoleno pouze v případě, že je daná položka volně disponibilní na skladě (systém vygeneruje doplatek).
  Po expedici (vyskladnění) je objednávka uzamčena proti změnám a jakýkoliv další požadavek zákazníka se řeší jako nová objednávka nebo vratka/reklamace.
- **Zdůvodnění:** Chrání sklad před odesláním neúplného či nezaplaceného zboží a udržuje soulad mezi platbou, rezervací a fyzickým výdejem.

### ADR 6: Volba technologického stacku (Python ekosystém)
- **Rozhodnutí:** Projekt bude realizován v programovacím jazyce **Python (3.11+)** s využitím moderního webového frameworku **FastAPI**, relační databáze **PostgreSQL 16**, ORM nástroje **SQLAlchemy 2.0** a migračního systému **Alembic**. Pro pilotní klientské rozhraní se využije šablonovací engine **Jinja2 s responzivním Vanilla CSS** a automatická interaktivní dokumentace **OpenAPI / Swagger UI**.
- **Zdůvodnění:** Python a FastAPI umožňují čisté oddělení tří vrstev, striktní typování pomocí Pydantic schémat, automatickou tvorbu API dokumentace pro e-shop a rychlé nasazení do Docker kontejnerů s minimální režií.

---

## 🗄️ Datový model a doménové entity

Navržený datový model plně pokrývá požadavky na minimálně 5 entit, M:N vazby a auditní sledování pohybů:

```mermaid
erDiagram
    PRODUCT ||--o{ PRODUCT_CATEGORY : has
    CATEGORY ||--o{ PRODUCT_CATEGORY : contains
    PRODUCT ||--o{ WAREHOUSE_STOCK : "stocked in"
    WAREHOUSE ||--o{ WAREHOUSE_STOCK : maintains
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--o{ ORDER_ITEM : includes
    PRODUCT ||--o{ ORDER_ITEM : "ordered as"
    WAREHOUSE ||--o{ ORDER : "dispatched from"
    PRODUCT ||--o{ STOCK_MOVEMENT : tracks
    WAREHOUSE ||--o{ STOCK_MOVEMENT : "source/target"

    PRODUCT {
        uuid id PK
        string code UK "SKU kód např. KAC-001-RED"
        string name "Název produktu"
        string description "Podrobný popis"
        decimal purchase_price "Nákupní cena bez DPH"
        decimal selling_price "Výchozí prodejní cena"
        int min_stock_level "Minimální požadovaná zásoba"
        boolean is_active "Aktivní v nabídce"
    }

    CATEGORY {
        uuid id PK
        string name UK "Název např. Pro batolata"
        string description "Popis kategorie"
    }

    PRODUCT_CATEGORY {
        uuid product_id PK, FK
        uuid category_id PK, FK
    }

    WAREHOUSE {
        uuid id PK
        string code UK "Kód např. WH-HK, WH-TREB"
        string name "Název skladu"
        string location "Adresa / umístění"
        boolean is_active "Aktivní sklad"
    }

    WAREHOUSE_STOCK {
        uuid id PK
        uuid warehouse_id FK
        uuid product_id FK
        int physical_quantity "Fyzický počet na regále (>= 0)"
        int reserved_quantity "Rezervováno v objednávkách (>= 0)"
    }

    STOCK_MOVEMENT {
        uuid id PK
        uuid product_id FK
        uuid source_warehouse_id FK "Odkud (null při příjmu od dodavatele)"
        uuid target_warehouse_id FK "Kam (null při výdeji zákazníkovi)"
        int quantity "Přemístěné množství (> 0)"
        string movement_type "RECEIPT | DISPATCH | TRANSFER | INVENTORY_CORRECTION"
        string note "Zdůvodnění např. Inventura garáž / Objednávka č. 1024"
        timestamp created_at "Čas provedení pohybu"
    }

    CUSTOMER {
        uuid id PK
        string first_name "Jméno"
        string last_name "Příjmení"
        string email "E-mail"
        string phone "Telefonní kontakt"
        string address "Doručovací adresa"
        timestamp created_at "Datum registrace"
    }

    ORDER {
        uuid id PK
        string order_number UK "Číslo objednávky (např. 2026-0001)"
        uuid customer_id FK
        uuid warehouse_id FK "Sklad určený pro expedici"
        string status "NEW | RESERVED | PAID | DISPATCHED | CANCELLED"
        decimal total_price "Celková částka objednávky"
        timestamp created_at "Datum a čas vytvoření"
        timestamp dispatched_at "Datum a čas fyzické expedice"
    }

    ORDER_ITEM {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        int quantity "Objednaný počet kusů (> 0)"
        decimal unit_price "Fixovaná prodejní cena za kus při koupi"
    }
```

### Popis klíčových vazeb a integritních pravidel
1. **M:N Vazba produktů a kategorií (`PRODUCT_CATEGORY`):** Každý produkt může náležet do libovolného počtu kategorií současně.
2. **Auditní stopa pohybů (`STOCK_MOVEMENT`):** Každá změna v tabulce `WAREHOUSE_STOCK` musí být doprovázena vložením záznamu do `STOCK_MOVEMENT`. Zajišťuje 100% zpětnou dohledatelnost („kde je ta káča...“).
3. **Fixace ceny v `ORDER_ITEM`:** Pole `unit_price` zachycuje okamžitou cenu v době nákupu; budoucí přecenění v tabulce `PRODUCT` tuto hodnotu nikdy neovlivní.
4. **Trvalost zákazníka (`CUSTOMER`):** Záznamy zákazníků se nemažou (pouze případně označí jako neaktivní), aby byly zachovány vazby pro reklamace.

---

## 🏛️ Architektura a vrstvy systému

Aplikace je navržena striktně podle požadavku na **tři vrstvy se závislostmi jedním směrem**:

```
+-----------------------------------------------------------------------------------+
|                           1. PREZENTAČNÍ VRSTVA                                   |
|  - Webové rozhraní pro skladníka (FastAPI + Jinja2 + Responsive Vanilla CSS)      |
|  - REST API routery pro e-shop (/api/products, /api/orders, Swagger UI na /docs)  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v (závisí na)
+-----------------------------------------------------------------------------------+
|                      2. APLIKAČNÍ A DOMÉNOVÁ VRSTVA                               |
|  - Byznys služby (ProductService, StockService, OrderService)                      |
|  - Validace doménových pravidel (Pydantic validátory, kontrola záporu a rezervací)|
|  - Doménové výjimky a transakční hranice                                          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v (závisí na)
+-----------------------------------------------------------------------------------+
|                   3. PERSISTENČNÍ A INFRASTRUKTURNÍ VRSTVA                        |
|  - Repozitáře (ProductRepository, StockRepository)                                |
|  - SQLAlchemy 2.0 mapování, relace a constraints                                 |
|  - Verzované databázové migrace přes Alembic                                      |
|  - PostgreSQL 16 v Docker kontejneru                                              |
+-----------------------------------------------------------------------------------+
```

---

## 🎨 Uživatelské rozhraní a ergonomie (UI/UX)

Na základě přání klienta („ať to jde používat z mobilu“ a „barevně, ať vidím, co hoří“) systém obsahuje:
- **Responzivní rozhraní pro mobil i tablet:** Velké dotykové ovládací prvky vhodné pro práci ve skladu i se čtečkou čárových kódů.
- **Barevný status dashboard:**
  - 🔴 **Kritická zásoba (Červená):** Aktuální zásoba je na nebo pod hodnotou `min_stock_level`. Položka se automaticky zobrazuje v seznamu „Co ihned doobjednat“.
  - 🟠 **Blíží se limitu (Oranžová):** Zásoba je v rozmezí 100 % – 130 % minimální hodnoty.
  - 🟢 **Dostatek (Zelená):** Zásoba je bezpečná.
- **Rychlý přehled skladů:** Přehledná matice zobrazující stav položky v Hradci Králové a v Garáži v Třebechovicích na jednom řádku.

---

## 🚀 Instalace a spuštění

Celé prostředí včetně relační databáze je připraveno ke spuštění pomocí **Docker Compose**:

### 1. Prerekvizity
- Docker Desktop a Docker Compose v aktuální verzi
- Git

### 2. Spuštění aplikace
V kořenovém adresáři projektu spusťte:
```bash
docker compose up --build
```
Tento příkaz:
1. Spustí kontejner s relační databází (PostgreSQL).
2. Provede automatické databázové migrace na nejnovější verzi schématu.
3. Naplní databázi syntetickými počátečními daty (katalog hraček, 2 sklady, demo zákazníci).
4. Spustí aplikační server a zpřístupní webové rozhraní.

### 3. Spuštění testů
```bash
# Spuštění automatizovaných testů byznys pravidel a integrity
docker compose run --rm app-tests
```

---

## 🗺️ Celkový fázový plán vývoje projektu (Roadmap)

Pro přehledný, iterativní a bezpečný vývoj je projekt rozdělen do **8 logických fází** podle principu *Tracer Bullet / Walking Skeleton* (od tenké spustitelné vertikály k postupnému nabalování doménové logiky):

```mermaid
flowchart TD
    F1["Fáze 1: Walking Skeleton & Docker"] --> F2["Fáze 2: Pilotní demo (Product)"]
    F2 --> F3["Fáze 3: Kategorie & M:N vazba"]
    F3 --> F4["Fáze 4: Sklady & Dvojí stav zásob"]
    F4 --> F5["Fáze 5: Pohyby & Audit trail"]
    F5 --> F6["Fáze 6: Zákazníci & Objednávky"]
    F6 --> F7["Fáze 7: Reporting po kategoriích"]
    F7 --> F8["Fáze 8: Testy & Obhajoba"]
```

| Fáze | Název fáze | Klíčový cíl a náplň | Hlavní výstup |
| :--- | :--- | :--- | :--- |
| **Fáze 1** | **Walking Skeleton & Infrastruktura** | Docker Compose (`app` + `db`), PostgreSQL 16, konfigurace SQLAlchemy 2.0 a Alembic migrací. | Běžící skeleton na 1 příkaz, `/docs` a `/health`. |
| **Fáze 2** | **Pilotní demo – Správa produktů (`Product`)** | Kompletní 3vrstvá vertikála pro dřevěné hračky: ORM, repozitář, service s validací marží/cen, REST API a responzivní web UI. | **Demo pro klienta/vyučujícího na cvičení** pro 1. feedback. |
| **Fáze 3** | **Kategorie a M:N vazba (`Category`)** | Zavedení kategorií a vazební tabulky `ProductCategory` (splnění povinného minima M:N). Filtrování v katalogu. | Tatáž hračka ve více kategoriích naráz. |
| **Fáze 4** | **Sklady a Zásoby (`Warehouse`, `Stock`)** | Evidence 2 skladů (Hradec Králové vs. Garáž Třebechovice). Dvoustupňový model: fyzická vs. rezervovaná zásoba. | Dashboard skladu s indikací „co hoří“ pod minimem. |
| **Fáze 5** | **Pohyby a Auditní stopa (`StockMovement`)** | Vynucení zákazu záporu (`quantity >= 0`). Audit 100 % pohybů (příjem, transfer Hradec-Třebechovice, inventurní vyrovnání). | Zpětná dohledatelnost („kde je ta káča...“). |
| **Fáze 6** | **Zákazníci a Objednávky (`Customer`, `Order`)** | Rezervace při objednání, neměnnost prodejní ceny v `OrderItem`, fyzický odpis při expedici, zákaz mazání zákazníků. | Kompletní nákupní a expediční proces z e-shopu. |
| **Fáze 7** | **Reporting a Analytika** | Měsíční obrat po kategoriích, přehled ziskovosti a automatický seznam položek k doobjednání. | Manažerské výkazy pro majitele Petra Doležala. |
| **Fáze 8** | **Testy, optimalizace a Obhajoba** | Komplexní sada unit/integračních testů v `pytest`, revize SSOT dokumentace, finální verifikace před odevzdáním. | Projekt připravený k bezchybné obhajobě. |

---

## 🛠️ Implementační plán – Pilotní demo (Správa entit Product)

Cílem pilotního dema je vytvořit **funkční, minimální, ale architektonicky kompletní vertikálu** (všechny 3 vrstvy + DB + Docker) spravující centrální entitu systému: **`Product` (Dřevěná hračka)**. Toto demo bude předvedeno klientovi (vyučujícímu) pro získání první zpětné vazby.

### Proč právě entita `Product`?
1. Je to ústřední byznys entita firmy *Dřevěnka s.r.o.* (hračky, káči, koníci, vláčky).
2. Okamžitě demonstruje nahrazení chaotické excelovské tabulky strukturovaným katalogem.
3. Demonstruje povinné atributy zadání: název, SKU kód, popis, nákupní cena, prodejní cena, minimální zásoba.
4. Připravuje půdu pro navázání kategorií (M:N) a skladových zásob (Hradec Králové vs. Třebechovice).

### Fáze realizace pilotního dema:

```
[Krok 1: Kostra projektu] ---> [Krok 2: Persistenční vrstva] ---> [Krok 3: Aplikační logika]
(Dockerfile, Compose, DB)      (SQLAlchemy, Alembic migrace)      (Pydantic, ProductService)
                                                                           |
[Krok 6: Předvedení klientovi]<-- [Krok 5: Testy a seed dat] <--- [Krok 4: Prezentační vrstva]
(Zpětná vazba, cvičení)        (pytest, demo data hraček)         (REST API + Webové UI)
```

#### Krok 1: Inicializace skeletonu, Dockeru a databáze
- Vytvoření souborů `Dockerfile`, `docker-compose.yml`, `requirements.txt` a `.env.example`.
- Nastavení služeb:
  - `db`: PostgreSQL 16 s trvalým svazkem (volume) a healthcheckem.
  - `web`: Python 3.11+ / FastAPI aplikace s automatickým reloadem pro vývoj.
- Nastavení centrálního konfiguračního modulu `app/core/config.py` a správy DB spojení `app/core/database.py`.

#### Krok 2: Persistenční vrstva (Infrastruktura a migrace)
- Inicializace migračního nástroje **Alembic** (`alembic/`).
- Definice ORM modelu `Product` v `app/infrastructure/db/models.py` (včetně kontrolních omezení `selling_price >= 0`, `purchase_price >= 0` a unikátnosti `code`).
- Vytvoření a aplikace první migrace `001_create_products_table`.
- Implementace `ProductRepository` v `app/infrastructure/repositories/product_repository.py` (metody `list_all`, `get_by_id`, `get_by_code`, `create`, `update`, `delete/deactivate`).

#### Krok 3: Aplikační a doménová vrstva (Byznys logika)
- Definice DTO / Pydantic schémat v `app/domain/models/product.py`:
  - `ProductCreate`, `ProductUpdate`, `ProductResponse`.
- Implementace doménových výjimek v `app/domain/exceptions.py` (`ProductNotFoundError`, `DuplicateProductCodeError`, `InvalidPriceError`).
- Implementace `ProductService` v `app/domain/services/product_service.py` s validací byznys pravidel:
  - Zajištění unikátnosti SKU kódu před uložením.
  - Kontrola, že prodejní cena je vyšší než nákupní (varování / validace marže).
  - Validace nezápornosti cen a minimální skladové hladiny.

#### Krok 4: Prezentační vrstva (REST API a Web UI pro klienta)
- **REST API:**
  - Vytvoření routeru `app/presentation/api/product_router.py` s endpointy:
    - `GET /api/products` (seznam s možností filtrování / vyhledávání)
    - `GET /api/products/{id}` (detail produktu)
    - `POST /api/products` (založení nového produktu)
    - `PUT /api/products/{id}` (úprava cen, minimální zásoby či popisu)
  - Automatická interaktivní dokumentace na `/docs` (Swagger UI).
- **Web UI pro skladníka a klienta:**
  - Šablony Jinja2 v `app/presentation/templates/`:
    - `base.html` – přehledný layout, responzivní pro mobil i desktop.
    - `product_list.html` – katalog dřevěných hraček, vyhledávací pole, barevné indikátory cen a stavů.
    - `product_form.html` – intuitivní formulář pro přidání/editaci hračky.
  - Vlastní čistý CSS styl `app/presentation/static/css/style.css` (moderní design, žádné zbytečné externí knihovny, ergonomické pro mobilní skladníky).

#### Krok 5: Syntetická data a automatizované testy
- Vytvoření seedovacího skriptu s realistickými dřevěnými hračkami Dřevěnky (např. *Buková káča*, *Dřevěný vláček s vagóny*, *Tahací kačer*, *Houpací koník*, *Stavebnice z kostek*).
- Zavedení automatizovaných testů pomocí `pytest`:
  - Unit testy `ProductService` (validace cen, ošetření duplicitního kódu).
  - Integrační test API endpointů.

---

## 📝 Deník postupu a historie změn (Changelog)

- **2026-09-30 (Fáze 0 – Inicializace a stanovení SSOT):**
  - Inicializován Git repozitář a nastavena hlavní větev `main`.
  - Propojen vzdálený repozitář `https://github.com/ZdenekPese/ppro2026.git`.
  - Nastaveno pravidlo repozitáře: **striktní zákaz automatického pushování bez explicitního povelu uživatele**.
  - Zaveden Git pre-commit hook (`.git/hooks/pre-commit`) vynucující synchronizaci kódu a dokumentace.
  - Vytvořena komplexní technická dokumentace a rozpracována rozhodnutí pro **Zadání B (Sklad pro malý e-shop - Dřevěnka s.r.o.)**.
  - Vytvořen kořenový konfigurační soubor [AGENTS.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/AGENTS.md) definující pravidla a standardy pro AI asistenty.
  - Zaveden verzovaný Git hook v `.githooks/pre-commit` a nastaveno `git config core.hooksPath .githooks`.
  - Schválen technologický stack (Python 3.11+, FastAPI, PostgreSQL 16, SQLAlchemy 2.0, Alembic) – zaznamenáno v ADR 6.
  - Vypracován podrobný implementační plán pro pilotní demo spravující entitu `Product`.
- **2026-10-07 (Fáze 0 – Strukturování etap projektu):**
  - Rozpracována celková 8fázová roadmapa vývoje celého projektu od skeletonu po finální obhajobu.
  - Aktualizována pravidla v [AGENTS.md](file:///c:/Users/zzden/OneDrive/Dokumenty/ppro2026/AGENTS.md) pro fázový iterativní postup.
- **2026-10-07 (Fáze 1 – Walking Skeleton & Infrastruktura dokončena):**
  - Vytvořen `Dockerfile` (Python 3.12-slim) a `docker-compose.yml` (služby `web` a `db` s PostgreSQL 16 a healthcheckem).
  - Vytvořena konfigurace závislostí `requirements.txt` a vzor `.env.example`.
  - Založena modulární třívrstvá struktura projektu (`core`, `domain`, `infrastructure`, `presentation`).
  - Nastaveno databázové spojení SQLAlchemy v `app/core/database.py` a migrační nástroj Alembic (`alembic.ini`, `alembic/env.py`).
  - Implementován `health_router` na `/api/health` s testem spojení na databázi.
  - Vytvořen základní responzivní design systém v `app/presentation/static/css/style.css` a Jinja2 layout `base.html`.
  - Upraveno volání `TemplateResponse` pro plnou kompatibilitu s novějšími verzemi Starlette/FastAPI.
  - Přidány základní unit testy v `tests/test_health.py` (úspěšně ověřeny v běžícím Docker kontejneru).
- **2026-10-07 (Fáze 2 – Pilotní demo: Správa produktů Product dokončena):**
  - Vytvořen SQLAlchemy ORM model `Product` s integritními omezeními (unikátní SKU, nezáporné ceny, nezáporná minimální zásoba).
  - Vygenerována a aplikována 1. databázová migrace `b996581df047_create_products_table.py` přes Alembic.
  - Implementován `ProductRepository` s metodami CRUD a fulltextovým vyhledáváním.
  - Vytvořena doménová a byznys vrstva: Pydantic schémata (`ProductCreate`, `ProductUpdate`, `ProductResponse`), výjimky a `ProductService` s validací pravidel.
  - Vytvořeno REST API rozhraní `/api/products` (CRUD operace, Swagger na `/docs`).
  - Vytvořeno webové klientské UI na `/products` s katalogem dřevěných hraček, vyhledáváním a formulářem pro přidání a editaci položky.
  - Vytvořen seedovací skript `app/infrastructure/db/seed.py` naplňující 5 typických hraček Dřevěnky (Káča, Vláček, Tahací kačer, Houpací koník, Kostky).
  - Napsány automatizované testy v `tests/test_products.py` (ověření unikátnosti SKU, odmítnutí záporných cen, vyhledávání). Všech 6 testů úspěšně prochází.
- **2026-10-19 (Konfigurace IDE a typové kontroly):**
  - Přidána konfigurace `pyproject.toml`, `pyrightconfig.json` a `.vscode/settings.json`.
  - Pomocí moderního nástroje `uv` bylo v projektu inicializováno plnohodnotné lokální virtuální prostředí `.venv` s nativním Pythonem 3.12.15 a všemi závislostmi.
  - Editor nyní disponuje plně funkčním interpretrem a bezchybným IntelliSense.
  - Aktualizována idempotence testů v `tests/test_products.py`. Všechny testy procházejí jak lokálně, tak v Docker kontejneru.
