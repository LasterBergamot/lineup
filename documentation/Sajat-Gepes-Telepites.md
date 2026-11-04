# Saját gépes telepítés

Hogyan futtasd a Lineup saját példányát egyetlen, folyamatosan bekapcsolt gépen (NAS-on vagy kis szerveren),
lépésről lépésre, olyanoknak írva, akik még soha nem használtak terminált. Az angol változat, ugyanazokkal a
lépésekkel, ugyanabban a sorrendben: [[Self Hosting Guide]]. A fejlesztőknek szóló műszaki leírás (felépítés,
részletek): [[Self Hosting Reference]].

Ebben az útmutatóban végig a `lineup.example.com` címet használjuk példaként. Ahol ezt látod, a **saját címedet** írd be. Ha például a `example.net` domaint vetted meg, a címed `https://example.net` (előtte nincs `lineup.`, a végén pedig nincs perjel).

Ha egy lépésnél az áll, hogy kérj segítséget, fordulj ahhoz, aki az útmutatót adta. Ha nincs ilyen, nyiss egy hibajegyet (issue) a projekt GitHub-oldalán, és írd le, mit csináltál és mit láttál; jelszót, tokent vagy titkos kulcsot soha ne írj bele.

Tartalom:

1. [Mi ez?](#1-mi-ez)
2. [Mielőtt hozzákezdesz](#2-mielőtt-hozzákezdesz)
3. [Telepítés](#3-telepítés)
4. [Működik-e?](#4-működik)
5. [Személy hozzáadása vagy törlése](#5-személy-hozzáadása-vagy-törlése)
6. [Mindennapok](#6-mindennapok)
7. [Frissítés](#7-frissítés)
8. [Biztonsági mentések](#8-biztonsági-mentések)
9. [Visszaállítás](#9-visszaállítás)
10. [Ha valami nem működik](#10-ha-valami-nem-működik)

---

## 1. Mi ez?

A Lineup általában a felhőben fut. Ez az útmutató a **második, választható módról** szól: a saját példányodról,
amely egy olyan gépen fut, ami a tiéd (vagy egy megbízható emberé), és folyamatosan be van kapcsolva. A példánynak saját
adatai és saját listája van arról, ki jelentkezhet be. A felhős példánnyal semmit nem oszt meg.

**Mit kapsz a végén?** Egy webcímet, például `https://lineup.example.com`, amely bármelyik telefonról vagy
számítógépről megnyílik. Az emberek a Google-fiókjukkal jelentkeznek be, és csak azok léphetnek be, akiket felvettél
egy listára. A gép nem nyit ki egyetlen "ajtót" sem az internet felé, és a routeren sem kell semmit átállítanod: a kapcsolat egy úgynevezett alagúton (tunnel, lásd lentebb) halad át, és ez védi a gépet.

**Mennyi idő?** Az első beállításhoz számolj nagyjából egy órával (néha ráadásul akár egy napot is várni kell, amíg egy frissen vett domain aktívvá válik, lásd a 2.3 pontot). Ennek nagy része fiókok létrehozása és értékek
másolgatása egyik weboldalról a másikra. Utána a mindennapokban nincs teendő, egy frissítés pedig pár perc.

**Mennyibe kerül?** A domain, nagyjából 10 euró évente. A Cloudflare és a Google szolgáltatásai ingyenesek, a Lineup is
ingyenes. A gép és az áram a tiéd.

**Ki végezze az első beállítást?** Valaki, aki figyelmes, de nem kell informatikusnak lennie: fiókokat hozol létre,
értékeket másolsz át pontosan, és beírsz néhány parancsot. Ha egy receptet el tudsz készíteni, ezt is meg tudod csinálni.
Segít, ha ketten vagytok, és az egyikőtök felolvassa a lépéseket.

**Szavak, amikkel találkozni fogsz.** Mindegyiket egyszer itt magyarázzuk el:

- **Terminál**: egy ablak, amelybe parancsot gépelsz, és Entert nyomsz, ahelyett hogy kattintanál. Az útmutatóban minden parancs szürke dobozban vagy visszaidézőjelek között áll: másold be pontosan. A 2.1 pontban megmutatjuk, hogyan nyiss egyet.
- **SSH**: egy mód, amellyel a saját számítógépedről hálózaton át terminált nyithatsz egy másik gépen. Így a másolás-beillesztés is kényelmesebb.
- **Docker**: egy program, amely más programokat zárt dobozokban (konténerekben) futtat, hogy ne zavarják a gépet.
  A Lineup ilyen dobozok csomagjaként érkezik. Annyit kell tudnod, hogy a Dockernek telepítve kell lennie és futnia kell.
- **Domain**: egy weboldal neve, például `lineup.example.com`. Évente egyszer kell fizetned érte.
- **Alagút (tunnel)**: egy privát "cső" a gépedtől a Cloudflare-ig (egy cég, amely az internet egy részét működteti).
  A látogatók a Cloudflare-hez fordulnak, a Cloudflare a csövön át továbbítja a kérést a gépedhez. Mivel a gép maga kapcsolódik a
  Cloudflare-hez, kívülről senkinek sem kell tudnia csatlakozni hozzá.
- **`.env` fájl**: egy rejtett beállításfájl, amelyet a telepítő hoz létre a gépen. Ebben van minden jelszó, amelyre a Lineup-nak szüksége van. A 3.4 pontban elmentesz belőle egy másolatot.
- **Kliensazonosító, kliens titkos kulcsa és token**: hosszú szövegek, amelyek felhasználónévként és jelszóként működnek két szolgáltatás között (itt: a Google és a Lineup, illetve a Cloudflare és a Lineup között). Kezeld őket jelszóként.
- **Biztonsági mentés**: az adatok másolata, hogy egy véletlen hibát vagy egy félresikerült frissítést vissza lehessen csinálni.
  A Lineup mentései hogyan működnek, és mi ellen **nem** védenek, a [8. részben](#8-biztonsági-mentések) olvasható.
  Kérlek, olvasd el, mielőtt valódi adatot viszel fel.

**Még egy dolog, mielőtt valódi emberek használják.** A Lineup saját üzemeltetése **nem** mentesít az
európai adatvédelmi törvény (GDPR) alól. Aki üzemelteti, az felel az emberek adataiért. Amíg a *Privacy and Security* wikioldal ([[Privacy and Security]]) önüzemeltetett példányokról szóló részében lévő adatvédelmi ellenőrzőlistát nem teljesítettétek, a Lineup-on belül csak kitalált neveket és adatokat használj. Az ellenőrzőlistát az végzi el, aki a telepítést üzemelteti; az, hogy a kipróbáláshoz valódi Google-fiókkal jelentkezel be, nem gond.

**Megjegyzés a menüpontok neveiről.** A Cloudflare és a Google gyakran változtatja a menüit, ezért ebben az útmutatóban
nincsenek képernyőképek. A gombokat úgy nevezzük meg, ahogy az írás idején hívják őket; ha nem találod, **keresd a hozzá leginkább hasonló feliratot**.

**Az értékeket egyetlen privát jegyzetben gyűjtsd.** Az alábbi lépésekben összegyűjtesz néhány értéket (egy címet, egy
tokent, egy kliensazonosítót). Ezeket egy **jelszókezelő biztonságos jegyzetében** tartsd a saját számítógépeden, soha ne e-mailben vagy
csevegőben. (Macen vagy Linuxon használhatsz privát szövegfájlt is: terminálban futtasd ezt:
`mkdir -p ~/.config/lineup && touch ~/.config/lineup/selfhost.env && chmod 600 ~/.config/lineup/selfhost.env`, és nyisd meg bármelyik szövegszerkesztővel.) Az útmutató minden `NÉV=érték` sora ebbe a jegyzetbe kerül.

---

## 2. Mielőtt hozzákezdesz

Hat dolognak kell készen állnia a telepítés előtt. Nem nagyon függnek egymástól, bármilyen sorrendben megcsinálhatod
őket, de mindet meg kell csinálni.

### 2.1 A gép ellenőrzése

A gépnek folyamatosan be kell lennie kapcsolva, telepített Dockerrel, legalább 2 GB memóriával (a 4 GB kényelmes)
és legalább 10 GB szabad hellyel.

**Hogyan nyiss terminált a gépen?** A legegyszerűbb a saját számítógépedről, SSH-val. NAS-on először keresd a beállításokban a "Terminal" vagy "SSH" pontot, és kapcsold be. Aztán:

- Windowson nyisd meg a Start menüt, írd be: `PowerShell`, és nyomj Entert; Macen nyomd meg a Cmd+Szóköz billentyűt, írd be: `Terminal`, és nyomj Entert;
- írd be: `ssh nev@cim`, és nyomj Entert, ahol a `nev` a gép rendszergazdai felhasználóneve, a `cim` pedig a gép hálózati címe (a NAS saját admin oldalán, vagy a routered eszközlistájában találod);
- először megkérdezi: "Are you sure you want to continue connecting?": írd be: `yes`. Utána a jelszót kéri: **gépelés közben nem jelenik meg semmi**, ez normális; nyomj Entert;
- ezt az ablakot hagyd nyitva az egész útmutató alatt. Beillesztéshez használd a jobb egérgombot, vagy a Ctrl+Shift+V billentyűt (Macen a Cmd+V-t).

Ha a gépnek van képernyője és billentyűzete, vagy saját terminálalkalmazása, azt is használhatod.

Olyan mappába telepíts, amelyben bőven van szabad hely (NAS-on a fő adattérfogaton, nem a kis rendszerlemezen lévő mappába). Menj oda a `cd` paranccsal és a mappa útvonalával; az alábbi parancs így **azt** a mappát ellenőrzi. Ha bizonytalan vagy, használd a saját mappádat: `cd ~`.

**Teendő.** A gép terminálján másold be ezt a sort, és nyomj Entert:

```bash
uname -m; grep MemTotal /proc/meminfo; df -h .; docker --version; docker compose version
```

**Ezt kell látnod.** Öt-hat sort:

- `x86_64` vagy `aarch64` (a processzor fajtája; mindkettő jó),
- `MemTotal:` után egy legalább nagyjából 1900000 értékű szám (ez kilobájt: nagyjából 2 GB),
- egy kis táblázat, amelynek **utolsó sorában** az **Avail** oszlop legalább 10G (M, G vagy T betűvel is írhatja),
- `Docker version` után egy 20-nál nem kisebb számmal kezdődő verziószám,
- `Docker Compose version v2.20` vagy újabb.

**Ha nem ezt látod.** A `docker: command not found` azt jelenti, hogy a Docker nincs telepítve: NAS-on telepítsd a gyártó
alkalmazásközpontjából (keresd a "Docker" vagy "Container Manager" nevet). Ha a Docker "socketjére" vonatkozó `permission denied` hibát kapsz, a felhasználód nem használhatja a Dockert: jelentkezz be a NAS rendszergazdai fiókjával, vagy írd a parancs elé: `sudo` (és később minden `./lineup.sh` parancs elé is). `'compose' is not a docker command`, vagy 2.20-nál régebbi Compose-verzió: frissítsd a Dockert vagy a Container Managert az alkalmazásközpontból. Ha 2 GB-nál kevesebb a memória, vagy a
Docker nem telepíthető, ez a gép nem alkalmas. Itt állj meg, és kérj segítséget.

### 2.2 Ki viseli a gép gondját?

Valakinek le kell futtatnia a frissítéseket, és ha kell, a visszaállítást. Válaszd ki most ezt a személyt (a gép karbantartóját). A frissítések
nem maguktól történnek (ez szándékos: kívülről semmi nem tud a gépbe csatlakozni), ezért a karbantartónak időnként le kell futtatnia egy parancsot. A karbantartó gondoskodik a domain megújításáról is (lásd a 2.3 pontot).

**Teendő.** Írd fel a jegyzetedbe, ki az. Ha ő nem a géphez ülve dolgozik, hanem a saját számítógépéről, akkor SSH-ra van szüksége (lásd a 2.1 pontot). A kipróbálás nem kötelező: a saját számítógépén terminálban futtassa ezt:
`ssh nev@cim docker ps` (a valódi felhasználónévvel és gépcímmel), és nézze meg, hogy megjelenik-e a
konténerek táblázata, akár üresen is. Ha a karbantartó mindig a géphez ülve dolgozik, ezt a próbát hagyd ki.

**Ezt kell látnod.** Egy `CONTAINER ID` kezdetű fejlécsor, akkor is, ha alatta nincs semmi.

**Ha nem ezt látod.** `Connection refused`: az SSH ki van kapcsolva a gépen. `Permission denied (publickey,password)`: rossz felhasználónév vagy jelszó. Ha a hiba a Docker socketre vonatkozik, nézd meg a 2.1 pont Docker-megjegyzését. A próbát ki is hagyhatod, mindent meg lehet csinálni magán a gépen is.

### 2.3 A domain megvétele és hozzáadása a Cloudflare-hez

**Teendő.**

1. Hozz létre egy [Cloudflare](https://dash.cloudflare.com/sign-up)-fiókot. Ha van közös postaládátok
   (például `iroda@egyesulet.example`, nem egy ember privát levelezése), azt add meg. A profilbeállításokban kapcsold be a **kétlépcsős azonosítást** (minden belépésnél kell egy kód a telefonodról): ezen a fiókon keresztül lehet elérni a gépet.
2. Vegyél egy domaint (egy `example.net`-hoz hasonló nevet), nagyjából 10 euró évente, és kapcsold be az **automatikus megújítást** (auto-renew): ha a domain lejár, az oldal szó nélkül leáll. Döntsétek el, ki fizeti és ki újítja meg. A legegyszerűbb a **Cloudflare Registrar**, mert így máshol semmit nem kell intézned. Ha nem kapható nála a kívánt végződés (például `.com` vagy `.hu`), vedd meg máshol, add hozzá a Cloudflare-hez (keresd az "Add a domain"
   gombot), és az eladónál írd át a névszervereket (nameserver) arra a kettőre, amelyet a Cloudflare mutat (úgy néznek ki, mint `xxx.ns.cloudflare.com`; az eladó DNS-beállító oldalán kell beírnod őket). Olyan nevet
   válassz, amelyből nem derül ki, hol van a gép (ne legyen benne utca vagy lakóhely neve).
3. Írd a privát jegyzetedbe: `PUBLIC_URL=https://lineup.example.com`, a saját domainaddal és **perjel nélkül a végén**.

**Ezt kell látnod.** A domained a Cloudflare irányítópultján (dashboard) **Active** állapotban.

**Ha nem ezt látod.** Ha máshol vett domainnél "Pending nameserver update" áll, az eladónál a névszerverek átírása még nem
lépett életbe. Ez akár egy napig is eltarthat. Közben megcsinálhatod a 2.4 pont 1-3. lépését, de a 2.4 pont 4. lépése és a 2.5 pont előtt várd meg az **Active** állapotot.

### 2.4 Az alagút létrehozása

**Teendő.**

1. A Cloudflare irányítópultján nyisd meg a **Zero Trust** részt, és válaszd az ingyenes (**Free**) csomagot. Kérhet csapatnevet (bármi megfelel). Egyesek
   szerint az ingyenes csomagnál is bankkártyát kér. Ha így van, az ingyenes csomagon nem szabadna pénzt levonnia:
   mielőtt jóváhagyod, ellenőrizd az oldalon.
2. Menj ide: **Networks → Tunnels → Create a tunnel**, válaszd a **Cloudflared** típust, és nevezd el `lineup`-nak.
3. Az oldal egy telepítő parancsot mutat, amelyben a `--token` után egy hosszú szöveg áll. Másold ki **csak ezt a hosszú
   szöveget** (a tokent: általában `eyJ`-vel kezdődik, a parancs végéig tart, és nincs benne szóköz; bármelyik fül mutatja), és írd a privát jegyzetedbe így: `TUNNEL_TOKEN=<a hosszú szöveg>`. **Ne futtasd le azt a
   parancsot**: az alagutat a Lineup indítja el magától.
4. Adj hozzá egy **Public hostname**-et: a domained, **aldomain és útvonal nélkül**. A szolgáltatás típusa legyen `HTTP`,
   az URL pedig `web:8080`. Ezt **pontosan** így írd be: nem elírás és nem weboldal, a Lineup saját webes részének belső neve.
5. Nyisd meg magának a domainnek a beállításait (a Cloudflare fő irányítópultján, nem a Zero Trustban: válaszd ki a domainedet, és nézd át a menüit, például a Speed, Security, SSL/TLS és Web Analytics pontokat), és kapcsold **ki** ezt a négyet, mert szkripteket illesztenek az oldalakba,
   vagy blokkolják az alkalmazás saját forgalmát: **Web Analytics**, **Rocket Loader**, **Email Address Obfuscation**
   és **Bot Fight Mode**. Kapcsold **be** az **Always Use HTTPS** beállítást. Ha valamelyik már ki van kapcsolva, hagyd úgy.

**Ezt kell látnod.** Az alagút a listában **Inactive** vagy "Down" állapottal. Ez rendben van: a telepítésig semmi nem
csatlakozik hozzá.

**Ha nem ezt látod.** Ha nem találod a "Zero Trust" menüt, nézd meg a bal oldali menüben a "Networks" vagy "Tunnels" pontot, vagy
keress rá az irányítópulton a "tunnel" szóra.

**Az analitika és a követés maradjon kikapcsolva.** A Lineup maga nem használ sütiket, analitikát, nyomkövetőket,
külső betűtípusokat vagy külső szkripteket, és ez szándékos: így nincs szükség hozzájárulást kérő felugró sávokra, és a
látogatások privátak maradnak. Kérlek, hagyd így. Ne kapcsold be a Cloudflare Web Analytics funkciót (vagy bármilyen
hasonló "insights" vagy "analytics" funkciót), ne tegyél Google Analytics-et vagy bármilyen követőszkriptet az oldalra, és
ne használj olyan Cloudflare-funkciót, amely átírja az oldalakat (Rocket Loader, Email Address Obfuscation, Zaraz). Ha
egy irányítópult felajánlja, hogy "segítségképpen" bekapcsol valamelyiket, a válasz: nem.

### 2.5 A Google-bejelentkezés létrehozása

Az emberek Google-fiókkal jelentkeznek be. A Google-nek tudnia kell az oldaladról, és megadhatod, mely fiókok használhatják.

Ehhez csinálj egy **új** Google Cloud-projektet, ne olyat használj, amelyet másra használsz. Az engedélyezett emberek
listája a projekthez tartozik.

**Teendő.**

1. Nyisd meg a [Google Cloud konzolt](https://console.cloud.google.com/) (jelentkezz be egy Google-fiókkal; ha feltételeket kell elfogadnod, fogadd el; bankkártya vagy számlázás nem kell), és hozz létre egy **New project**-et, például
   `lineup-selfhost` néven. Ha a konzol a Google Auth Platformnál egy **Get started** oldalt mutat (rövid űrlap az alkalmazás nevével és az e-mail-címeddel, ez az úgynevezett "consent screen"), előbb töltsd ki: az alkalmazás neve `Lineup`, kapcsolattartónak a saját e-mail-címed.
2. Keresd a **Google Auth Platform → Audience** részt. Válaszd az **External** típust és a **Testing** közzétételi
   állapotot. A **Test users** alatt vedd fel mindenkit, aki bejelentkezhet, **magadat is**, a Google e-mail-címével (Google-fióknak kell lennie). Csak ezek a
   fiókok léphetnek be. A "Testing" a helyes állapot: nem azt jelenti, hogy az alkalmazás félkész, hanem ettől érvényes az engedélyezett emberek listája.
3. Keresd a **Data access** részt, és ellenőrizd, hogy csak az `openid`, az `email` és a `profile` van kijelölve.
4. Keresd a **Clients → Create client** részt, és válaszd a **Web application** típust. Add meg:
   - Authorized JavaScript origin: `https://lineup.example.com`
   - Authorized redirect URI: `https://lineup.example.com/auth/v1/callback`

   (a saját címeddel, pontosan beírva; az elsőnek a végén nincs perjel; ez két külön mező, mindegyiknél van egy **Add URI** gomb).
5. A Google ezután megmutat egy kliensazonosítót (client id) és egy kliens titkos kulcsot (client secret). **A titkos kulcsot másold ki, mielőtt bezárod az ablakot**: lehet, hogy többé nem mutatja meg (ha elveszted, hozz létre újat). Írd őket a privát
   jegyzetedbe így: `GOOGLE_CLIENT_ID=<az azonosító>` és `GOOGLE_SECRET=<a titok>`.

**Ezt kell látnod.** A klienst a listában, az embereidet pedig a Test users alatt.

**Ha nem ezt látod.** Ha nem találod az **Audience** vagy a **Clients** pontot, valószínűleg még nem töltötted ki a **Get started** űrlapot (1. lépés): töltsd ki, aztán nézd meg újra. Keresd a hozzá leginkább hasonló feliratot; a Google időnként átnevezi ezeket a menüket.

### 2.6 A mentések korlátainak elolvasása és elfogadása

Itt nincs mit kattintani, de ez a te döntésed. Olvasd el, és gondold végig, hogy elfogadod-e:

> A biztonsági mentések minden éjjel lefutnak, és 30 napig megmaradnak, ugyanezen a gépen lévő mappában. **Nincsenek
> titkosítva**, és bárki elolvashatja őket, aki hozzáfér ehhez a géphez. Tévedések és sikertelen frissítések ellen
> védenek. **Ha ez a gép elvész vagy tönkremegy, minden adat elvész**, hacsak valaki kézzel át nem másolta máshová a
> mentési mappát. Mentsd el a `.env` fájlt is egy biztonságos, privát helyre: nélküle egy új gépen végzett
> visszaállításnál mindenki bejelentkezését és az adatbázis jelszavait újra be kell állítani.

(A `.env` a rejtett beállításfájl, amelyet a telepítő hoz létre; a 3.4 pontban elmented.)

Ha a gépnek van második lemeze, vagy van egy mappád egy másik eszközön (hálózati megosztás), válassz ott egy mappát a
mentéseknek, és írd a privát jegyzetedbe: `BACKUP_DIR=/ennek/a/mappanak/az/utja`. (NAS-on egy példa útvonal: `/volume1/backup`; a lemezeket az `ls /` vagy `ls /volume1` paranccsal nézheted meg.) Ha nem, hagyd üresen: amikor a telepítő a mentési mappát kérdezi, csak nyomj Entert, és a mentések a Lineup mappájában egy `backups` nevű mappába kerülnek, ami kezdetnek megfelel.

**Ezt kell látnod.** Semmit: ez döntés, nem művelet. A telepítő ugyanezt a szöveget mutatja, és egy szó beírásával kell
megerősítened.

**Ha nem ezt látod.** Ha ezek a korlátok nem elfogadhatók számodra, itt állj meg. A mentési mappa kézi, máshová másolása (8. rész)
sokkal biztonságosabbá teszi.

**Készen vagy?** A privát jegyzetedben ennek kell lennie: `PUBLIC_URL`, `TUNNEL_TOKEN`, `GOOGLE_CLIENT_ID`,
`GOOGLE_SECRET`, és ha választottál, `BACKUP_DIR`.

---

## 3. Telepítés

Ezt **a gépen** csinálod, terminálban (lásd a 2.1 pontot), abban a mappában, amelyet erre kiválasztottál (előbb menj oda a `cd` paranccsal, vagy írd be: `cd ~` a saját mappádhoz).

### 3.1 A Lineup letöltése a gépre

**Teendő.** Nyisd meg a [kiadások oldalát](https://github.com/LasterBergamot/lineup/releases), keresd meg a legújabb
kiadást, és jegyezd meg a verziószámát, például `v0.2.0`. (Azt keresd, amelyiken a **Latest** felirat áll; a **Pre-release** jelölésűt ne használd.) Aztán a terminálban futtasd egyenként (mindegyik után Enter) ezt a négy parancsot,
a `v0.2.0`-t **mind a hét helyen** kicserélve erre a verzióra:

```bash
curl -LO https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz
curl -LO https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz.sha256
sha256sum -c selfhost-v0.2.0.tar.gz.sha256
tar -xzf selfhost-v0.2.0.tar.gz
```

**Ezt kell látnod.** A harmadik parancs után: `selfhost-v0.2.0.tar.gz: OK`. (Ez a parancs egy ujjlenyomat alapján ellenőrzi, hogy a fájl hiánytalan és sértetlen-e.) Ez azt jelenti, hogy a letöltés hiánytalan és
sértetlen. A negyedik parancs nem ír ki semmit, és létrehoz egy `selfhost` nevű mappát.

**Ha nem ezt látod.** A `FAILED` azt jelenti, hogy a letöltés sérült vagy módosították: töröld a két fájlt (`rm selfhost-v0.2.0.tar.gz selfhost-v0.2.0.tar.gz.sha256`), kezdd elölről, és ne
menj tovább. `curl: command not found`: a `curl -LO` helyett használd a `wget` parancsot (például `wget https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz`). "Not found" oldal: rossz a
verziószám, vagy abban a kiadásban még nincs `selfhost` fájl; próbáld az előző kiadást.

### 3.2 A gép ismételt ellenőrzése

**Teendő.**

```bash
cd selfhost
pwd
./lineup.sh doctor
```

A `pwd` kiírja a **selfhost mappa** teljes útvonalát; ez lesz innentől a Lineup mappája. Írd a jegyzetedbe így: `LINEUP_DIR=<az útvonal>`: minden későbbi rész ennek a `cd` parancsával kezdődik. (A `doctor` csak ellenőriz, semmit nem változtat.)

**Ezt kell látnod.** Ellenőrzések listáját, mindegyik mellett OK, figyelmeztetés vagy hiba jelzéssel. A figyelmeztetést
(például kevés szabad hely) érdemes elolvasni, de nem akadályoz. Minden hibához tartozik egy sor, amely megmondja, hogyan
kell kijavítani.

**Ha nem ezt látod.** `No such file or directory`: nem a jó mappában vagy; előbb `cd` a mappába. `Permission denied`: futtasd a `chmod +x lineup.sh` parancsot, és próbáld újra (ha a hibaüzenet a Dockerről szól, lásd a 2.1 pontot). Minden **hibát** javíts ki,
mielőtt továbbmész.

### 3.3 A telepítő futtatása

**Teendő.** Legyen előtted a privát jegyzeted, és futtasd:

```bash
./lineup.sh install
```

A telepítő egymás után kérdez: a nyilvános cím (`https://lineup.example.com`, `https://`-sel kell kezdődnie, útvonal nélkül),
az alagút tokenje, a Google kliensazonosítója, a Google kliens-titka és a mentési mappa. Mindegyiket másold be a
jegyzetedből (jobb egérgomb, vagy Ctrl+Shift+V; Macen Cmd+V). A titoknál **semmi nem jelenik meg beillesztés közben**: ez normális, szándékosan rejtett. Ezután megmutatja
a 2.6 pontbeli mentési korlátokat, és megkér, hogy írd be: `IGEN` (angolul `YES`; ha magyar szöveget látsz, `IGEN`-t írj). A telepítő alapból magyarul szól;
ha felajánlja a nyelv kiválasztását, a magyart válaszd.

**Ezt kell látnod.** A telepítő létrehozza a saját jelszavait (soha nem mutatja meg őket), mindent elindít, végül
üzenetet ad arról, hogy a Lineup fut, megmondja a címet, és emlékeztet arra, mit kell elmentened. Az első alkalommal pár
percig tart, mert letölti a program összetevőit. Közben ne zárd be az ablakot; ha a kapcsolat megszakad, futtasd a `./lineup.sh status` parancsot, és kérj segítséget.

**Ha nem ezt látod.**

- "Már van `.env` fájl": ez biztonsági ellenőrzés. A telepítő nem írja felül a meglévő beállításokat, mert az
  kizárná a Lineup-ot a saját adatbázisából. Ha a Lineup már telepítve volt itt, használd a 7. részt (frissítés). Ha úgy gondolod, hogy ez az első telepítés, egy korábbi próbálkozás hagyta ott a fájlt: ne törölj semmit, kérj segítséget.
- Rossz értéket írtál be, és csak a telepítés után vetted észre (rossz token, titkos kulcs vagy cím): kérj segítséget; ki lehet javítani, de nem a telepítő újrafuttatásával.
- Egy értéket elutasít: olvasd el az üzenetet. Általában az `https://` hiányzik a cím elejéről, vagy perjel van a végén.
- A telepítő üzenettel leáll: olvasd el, javítsd, amit mond, és futtasd újra a `./lineup.sh install` parancsot, kivéve, ha
  már létrehozta a `.env` fájlt, mert akkor az üzenet megmondja, mit tegyél.

### 3.4 A `.env` fájl elmentése

A telepítő létrehozott egy `.env` nevű fájlt abban a mappában, ahol vagy. Ebben van minden jelszó, amelyre a Lineup-nak
szüksége van. Máshol **nincs** eltárolva.

**Teendő.** Másold ezt a fájlt egy biztonságos, privát helyre, amely **nem ezen a gépen van**: egy fájlokat is tároló
jelszókezelőbe (mellékletként egy biztonságos jegyzethez), vagy egy privát helyen őrzött pendrive-ra. A neve ponttal kezdődik, ezért a fájlkezelők elrejtik: a NAS fájlkezelőjében keresd a "rejtett fájlok megjelenítése" lehetőséget, aztán töltsd le a fájlt; vagy a saját számítógépedről: `scp nev@cim:/a/selfhost/utja/.env .` (a `pwd` által kiírt útvonallal). Ne küldd el e-mailben, és ne tedd olyan mappába, amelyet a NAS más használói is megnyithatnak.

**Ezt kell látnod.** A fájlt biztonságosan eltárolva, máshol. Nyisd meg a másolatot, és nézd meg, hogy nem üres-e (nagyjából 20 sor).

**Ha nem ezt látod.** Ha nem találod, a terminálban futtasd az `ls -a` parancsot a Lineup mappájában: a `.env` nevű fájl ott lesz a
listában.

---

## 4. Működik?

**Teendő.**

1. A terminálban menj a selfhost mappába (`cd` a jegyzetedben lévő útvonalra), futtasd egyszer a `./lineup.sh backup` parancsot (ez elkészíti az első mentést), majd a `./lineup.sh status` parancsot.
2. Bármelyik számítógépen vagy telefonon nyisd meg a `https://lineup.example.com` címet (a saját domainaddal).
3. Nyomd meg a bejelentkezés gombot, a nyitóoldalon, és jelentkezz be egy olyan Google-fiókkal, amely a tesztfelhasználók listáján van. A Google figyelmeztető oldalt mutathat arról, hogy nem ellenőrizte az alkalmazást: egy tesztalkalmazásnál ez várható; válaszd az **Advanced** pontot, majd lépj tovább az alkalmazásba.

**Ezt kell látnod.**

1. Konténerek listáját, mind futó állapotban, egy sort arról, hogy az alkalmazás rendben működik, az utolsó mentés korát
   (néhány perc, az imént készített mentés után), a szabad helyet és a jelenlegi verziót.
2. A Lineup nyitóoldalát.
3. Bejelentkezés után visszakerülsz a Lineup-ba, és létrehozhatsz egy csapatot (ha még nincs egy sem, az alkalmazás maga kéri).

**Ha nem ezt látod.**

- `No such file or directory`: rossz mappában vagy, előbb `cd` a selfhost mappába.
- A státusz hibát mutat: olvasd el a sort, majd lásd a [10. részt](#10-ha-valami-nem-működik).
- Az oldal nem nyílik meg: várj két percet (az alagútnak kell egy kis idő), majd lásd a 10. részt, "Az oldal nem érhető
  el".
- A Google **access blocked** üzenetet ad: a fiók nincs a tesztfelhasználók listáján. Lásd az 5. részt.

---

## 5. Személy hozzáadása vagy törlése

Azt, hogy ki léphet be, a Google tesztfelhasználói listája dönti el, nem a Lineup.

**Teendő.**

1. Nyisd meg a [Google Cloud konzolt](https://console.cloud.google.com/), és válaszd ki a Lineup-projektedet (a projekt neve felül látható, például `lineup-selfhost`).
2. Menj ide: **Google Auth Platform → Audience → Test users**.
3. Személy hozzáadásához válaszd az **Add users** gombot, és írd be a Google e-mail-címét. Törléséhez vedd ki a címét a
   listából. Mentsd.
4. Amint valaki be tud jelentkezni, egy meghívó linkkel csatlakozik egy csapathoz a Lineupban; a linket a csapat egy
   tagja készíti az alkalmazásban, a csapat oldalán, és elküldi neki.

**Ezt kell látnod.** Az új címet a listában. A személy innentől be tud jelentkezni.

**Ha nem ezt látod.** Ha a személy még mindig **access blocked** üzenetet kap, nézd meg, hogy pontosan azt a Google-fiókot használja-e
(nem egy másikat, amely ugyanabban a böngészőben be van jelentkezve), és várj egy percet.

Ha valakit kiveszel a listából, többé nem tud bejelentkezni, de az adatai nem törlődnek a Lineup-ból. Ha valaki az adatai
törlését vagy kiadását kéri, az külön feladat külön szabályokkal: lásd [[Privacy and Security]].

---

## 6. Mindennapok

Naponta semmit nem kell csinálni. A mentések éjjel maguktól lefutnak, és a Lineup magától újraindul, ha a gép újraindul.

**Havonta egyszer** (tegyél be egy emlékeztetőt a naptáradba) nyiss egy terminált a gépen, menj a selfhost mappába (`cd` a jegyzetedben lévő útvonalra), és futtasd:

```bash
./lineup.sh status
```

Három dolgot nézz meg: az alkalmazás rendben működik-e, az utolsó mentés **kevesebb mint másfél napos**-e, és van-e még szabad
hely (legalább 5 GB). A státusz azt is megmondja, hogy van-e újabb Lineup-verzió. A frissítések nem települnek maguktól: ha van újabb
verzió, ütemezz be egy frissítést (7. rész), legkésőbb néhány hónapon belül. Ha a gép áramszünet miatt leállt, a Lineup magától újraindul; a `status` megerősíti.

**Ezt kell látnod.** Egészséges alkalmazást és friss mentést.

**Ha nem ezt látod.** Lásd a [10. részt](#10-ha-valami-nem-működik).

---

## 7. Frissítés

**Teendő.** Válassz csendes időt (az alkalmazás rövid időre elérhetetlen), nyiss egy terminált a gépen, menj a selfhost mappába (`cd` a jegyzetedben lévő útvonalra), és futtasd (magadtól semmit nem kell letöltened, a frissítés elvégzi):

```bash
./lineup.sh update
```

Magától elvégzi ezeket, és közben tájékoztat: megkeresi a legújabb verziót, letölti, és ellenőrzi, hogy sértetlen-e,
**előbb mentést készít** (és leáll, ha a mentés nem sikerül, így soha nincs frissítés friss mentés nélkül), telepíti az új
verziót, és ellenőrzi, hogy működik-e.

Futás közben ne zárd be az ablakot. Ha egy adott verzióra akarsz lépni, add meg: `./lineup.sh update --version v0.2.0`.

**Ezt kell látnod.** Üzenetet arról, hogy a Lineup az új verzión fut, és rendben működik. Utána futtasd a `./lineup.sh status`
parancsot.

**Ha nem ezt látod.** Ha a frissítés nem sikerül, a szkript pontosan megmondja, mi történt. Két eset van:

- Azt írja, hogy a frissítést **visszavonta, és semmi nem veszett el**: a Lineup újra a régi verzión fut. Kérj segítséget, idézd az üzenetet, mielőtt újra próbálkoznál.
- Azt írja, hogy az **adatbázis megváltozott**: nem próbálkozik találomra. Kövesd az üzenetben lévő utasítást: megnevez egy
  visszaállító parancsot, amely a frissítés előtti mentésre áll vissza (9. rész).

Ne próbálkozz saját megoldással. Ha egyik üzenet sem jelenik meg, kérj segítséget.

A fejlesztők ugyanezt a frissítést a saját számítógépükről is el tudják indítani; lásd [[Self Hosting Reference]].

---

## 8. Biztonsági mentések

Ezt a részt olvasd el figyelmesen. Megmondja, mire jók a mentések, és mire nem.

> A biztonsági mentések minden éjjel lefutnak, és 30 napig megmaradnak, ugyanezen a gépen lévő mappában. **Nincsenek
> titkosítva**, és bárki elolvashatja őket, aki hozzáfér ehhez a géphez. Tévedések és sikertelen frissítések ellen
> védenek. **Ha ez a gép elvész vagy tönkremegy, minden adat elvész**, hacsak valaki kézzel át nem másolta máshová a
> mentési mappát. Mentsd el a `.env` fájlt is egy biztonságos, privát helyre: nélküle egy új gépen végzett
> visszaállításnál mindenki bejelentkezését és az adatbázis jelszavait újra be kell állítani.

Egyszerűen fogalmazva: a mentések akkor segítenek, ha valaki tévedésből töröl valamit, vagy egy frissítés félresikerül. Akkor nem
segítenek, ha a gépet ellopják, kigyullad, vagy a lemeze tönkremegy, mert a mentések ugyanazon a gépen vannak. Ennek
elkerülésére **másold át kézzel a mentési mappát máshová** időnként, például havonta egyszer.

Még két dolog, amit érdemes tudni. A mentésekben nincsenek benne az emberek bejelentkezési munkamenetei, ezért visszaállítás után
mindenkinek újra be kell jelentkeznie, és egy ellopott mentéssel nem lehet átvenni egy bejelentkezett munkamenetet. A 30
napnál régebbi mentések maguktól törlődnek.

**Mentés készítése most.** Futtasd: `./lineup.sh backup`. Kiírja a létrehozott fájlokat és a méretüket.

**A mappa kézi másolása máshová.**

1. Keresd meg a mappát: a jegyzetedben lévő `BACKUP_DIR`, vagy a selfhost mappában a `backups` nevű mappa.
2. Másold az egész mappát egy pendrive-ra, egy másik számítógépre vagy egy másik eszközre. NAS-on ez általában megoldható a
   fájlkezelővel (másold a mappát egy másik megosztásra vagy lemezre). Ha szeretnéd, SSH-val egy másik számítógépről az egyik mód:
   `scp -r felhasznalo@gepneve:/a/mentesek/utja ./lineup-mentesek` (a valódi felhasználóval, géppel és úttal). A mentések
   nincsenek titkosítva, ezért a másolatot is privát helyen tartsd, például egy pendrive-ot zárt fiókban.
3. A mappában éjszakánként két fájlt látsz, például `lineup-2026-11-04.dump` és `auth-2026-11-04.dump` néven (az egyik az
   adatoké, a másik a bejelentkezési fiókoké), meg egy kis `last-success` fájlt, amely az utolsó sikeres mentés idejét
   tartalmazza. Mindig mindet másold.

**Ezt kell látnod.** A másolatot az eredeti mellett, ugyanazokkal a fájlokkal.

**Ha nem ezt látod.** Ha a fájlok száma vagy a teljes méret (nézd a mappa tulajdonságait) eltér az eredetiétől, a másolás megszakadt: csináld újra.

Mielőtt valódi adat kerül bele, próbálj ki egyszer egy visszaállítást (9. rész), hogy megtudd, működik.

---

## 9. Visszaállítás

A visszaállítás az adatokat egy korábbi éjszaka állapotára viszi vissza. Akkor használd, ha olyan tévedés történt, amelyet
másképp nem tudsz helyrehozni, vagy ha a frissítés üzenete azt kéri.

**Mielőtt megcsinálod, tudd:** minden, amit az adott dátum **után** vittek be, **elvész**, és **mindenkinek újra be kell
jelentkeznie**.

**Teendő.** A gépen, terminálban, a selfhost mappában (`cd` a jegyzetedben lévő útvonalra):

```bash
./lineup.sh restore
```

Kilistázza azokat a dátumokat, amelyekhez van mentés, és megkérdezi, melyiket használja (írd be a dátumot, például 2026-11-03). Közvetlenül egy dátum kiválasztásához:
`./lineup.sh restore --date 2026-11-03` (a listában szereplő dátumot használd). Még egyszer figyelmeztet, és megkér, hogy
írd be: `VISSZAALLIT` (angolul `RESTORE`). Ezután **először biztonsági mentést készít a jelenlegi állapotról** (így még egy
téves visszaállítás is visszavonható), leállítja az alkalmazást, visszaállítja az adatokat, mindent elindít, és ellenőrzi,
hogy működik-e.

**Ezt kell látnod.** Üzenetet arról, hogy a visszaállítás befejeződött, és a Lineup rendben működik. Nyisd meg a címet, és
jelentkezz be újra.

**Ha nem ezt látod.** Ha a visszaállítás üzenettel leáll, kövesd az üzenetet. A biztonsági mentés miatt semmi nem vész el, ha
újrapróbálod. Ha az egész gép elveszett, az új gépen való visszaállításhoz kell a mentési mappa **és** az elmentett
`.env` fájl (3.4 pont): ehhez kérj segítséget; a lépések a műszaki oldalon vannak ([[Self Hosting Reference]], a mentésekről és a visszaállításról szóló rész).

---

## 10. Ha valami nem működik

| Amit látsz | Mit tegyél | Mikor kérj segítséget |
|---|---|---|
| **`./lineup.sh: No such file or directory`** | Rossz mappában vagy: `cd` a selfhost mappába (a jegyzetedben lévő útvonalra) | Nem találod a mappát |
| **A Docker "permission denied" hibát ad** | Használd a rendszergazdai fiókot, vagy írd a parancs elé: `sudo` (2.1 pont) | Így is hibázik |
| **Az oldal nem érhető el** (nem nyílik meg) | Be van-e kapcsolva a gép, és kapcsolódik-e a hálózathoz? Futtasd a `./lineup.sh status` parancsot: futnak-e a konténerek? A Cloudflare irányítópultján nyisd meg a **Networks → Tunnels** részt: a `lineup` **Healthy** (zöld) állapotú-e? Ha nem, indítsd újra a gépet (a NAS saját weboldalán válaszd a Restart pontot; a Lineup magától elindul), és várj pár percet | A gép be van kapcsolva, minden fut, az alagút csatlakozik, mégsem nyílik meg az oldal; vagy az alagút tokenjét megváltoztatták |
| **A bejelentkezés "access blocked" üzenetet ad** (vagy "this app is not verified", továbblépés nélkül) | A fiók nincs a tesztfelhasználók listáján. Add hozzá (5. rész) | A fiók rajta van a listán, és pár perc után is hibás |
| **A Google `redirect_uri_mismatch` hibát mutat** | A Google Cloud konzolban, a **Clients** alatt ellenőrizd, hogy az átirányítási URI pontosan `https://lineup.example.com/auth/v1/callback`, a te címeddel (2.5 pont; a Google Cloud konzolban a projekted **Clients** oldalát keresd) | Pontosan egyezik, és mégis hibás |
| **A bejelentkezés sikerül, de üres vagy hibás oldalra jutsz** | Futtasd a `./lineup.sh status` parancsot. Ha egy konténer nem működik rendben, várj egy percet, és nézd meg újra | Öt perc után sem lesz rendben |
| **A `status` szerint az utolsó mentés másfél napnál régebbi** | Futtasd a `./lineup.sh backup` parancsot, és olvasd el, mit ír. A szabad helyet a `./lineup.sh status` mutatja | A mentés nem sikerül, vagy a lemez majdnem tele van |
| **A lemez majdnem tele van** | Szabadíts fel helyet a gépen, vagy vidd máshová a régi mentéseket (előbb másold, aztán töröld) | Nem tudod, mit biztonságos törölni: a Lineup mappáját és a `.env` fájlt ne töröld |
| **Egy frissítés nem sikerült** | Pontosan azt tedd, amit az üzenet mond (visszavonva, vagy visszaállító parancs) | Az üzenet nem jelent meg, vagy nem érted |
| **Egy PDF nem töltődik le, vagy sokáig tart** | Várj egy percet, és próbáld újra. Nagyon ritkán előfordul, hogy sokan egyszerre készítenek PDF-et | Folyamatosan hibázik |
| **Az oldal működött, aztán hirtelen azt írja, hogy a domain nem elérhető** | Lehet, hogy a domain lejárt: nézd meg a megújítását (2.3 pont) | Nem tudod megújítani |
| **Visszaállítás után senki nincs bejelentkezve** | Ez várható. Mindenki újra bejelentkezik | Újbóli bejelentkezés után sem működik |

**Segítségkérés.** Mondd el, mit csináltál, mit láttál, és másold be a pontos üzenetet. Soha ne küldd el senkinek a `.env`
fájlodat, az alagút tokenjét vagy a Google kliens-titkát, és ne tedd ki őket nyilvános helyre: teljes hozzáférést adnak.
Ha azt gyanítod, hogy valamelyik kiszivárgott, az adatvédelmi incidens: kövesd a [[Breach Runbook]] oldalt.
