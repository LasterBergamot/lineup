# Saját gépes telepítés

Hogyan futtasd a Lineup saját példányát egyetlen, folyamatosan bekapcsolt gépen (NAS-on vagy kis szerveren),
lépésről lépésre, olyanoknak írva, akik még soha nem használtak terminált. Az angol változat, ugyanazokkal a
lépésekkel, ugyanabban a sorrendben: [[Self-Hosting Guide]]. A fejlesztőknek szóló műszaki leírás (felépítés,
részletek): [[Self-Hosting Reference]].

Ebben az útmutatóban végig a `lineup.example.com` címet használjuk. Cseréld a saját domainedre.

Tartalom:

1. [Mi ez?](#1-mi-ez)
2. [Mielőtt hozzákezdesz](#2-mielőtt-hozzákezdesz)
3. [Telepítés](#3-telepítés)
4. [Működik-e?](#4-működik-e)
5. [Személy hozzáadása vagy törlése](#5-személy-hozzáadása-vagy-törlése)
6. [Mindennapok](#6-mindennapok)
7. [Frissítés](#7-frissítés)
8. [Biztonsági mentések](#8-biztonsági-mentések)
9. [Visszaállítás](#9-visszaállítás)
10. [Ha valami nem működik](#10-ha-valami-nem-működik)

---

## 1. Mi ez?

A Lineup általában a felhőben fut. Ez az útmutató a **második, választható módról** szól: a saját példányodról,
amely egy olyan gépen fut, amely a tiéd (vagy egy megbízható emberé), és mindig be van kapcsolva. A példánynak saját
adatai és saját listája van arról, ki jelentkezhet be. A felhős példánnyal semmit nem oszt meg.

**Mit kapsz a végén?** Egy webcímet, például `https://lineup.example.com`, amely bármelyik telefonról vagy
számítógépről megnyílik. Az emberek a Google-fiókjukkal jelentkeznek be, és csak azok léphetnek be, akiket felvettél
egy listára. A gép nem nyit ki egyetlen "ajtót" sem az internet felé: a kapcsolat egy úgynevezett alagúton (tunnel,
lásd lentebb) megy át, ez tartja a gépet rejtve és biztonságban.

**Mennyi idő?** Az első beállításhoz számolj nagyjából egy órával. Ennek nagy része fiókok létrehozása és értékek
másolgatása egyik weboldalról a másikra. Utána a mindennapokban nincs teendő, egy frissítés pedig pár perc.

**Mennyibe kerül?** A domain, nagyjából 10 euró évente. A Cloudflare és a Google részei ingyenesek, a Lineup is
ingyenes. A gép és az áram a tiéd.

**Ki csinálja az első beállítást?** Valaki, aki figyelmes, de nem kell informatikusnak lennie: fiókokat hozol létre,
értékeket másolsz át pontosan, és beírsz néhány parancsot. Ha egy receptet követni tudsz, ezt is meg tudod csinálni.
Segít, ha ketten vagytok, és az egyikőtök felolvassa a lépéseket.

**Szavak, amikkel találkozni fogsz.** Mindegyiket egyszer itt magyarázzuk el:

- **Terminál**: egy ablak, amelybe parancsot gépelsz, és Entert nyomsz, ahelyett hogy kattintanál. NAS-on a
  beállításokban gyakran "Terminal" vagy "SSH" néven szerepel. Amit be kell gépelned, azt szürke dobozban látod:
  másold be pontosan.
- **Docker**: egy program, amely más programokat zárt dobozokban (konténerekben) futtat, hogy ne zavarják a gépet.
  A Lineup ilyen dobozok csomagjaként érkezik. Annyit kell tudnod, hogy a Dockernek telepítve kell lennie és futnia kell.
- **Domain**: egy weboldal neve, például `lineup.example.com`. Évente egyszer fizeted.
- **Alagút (tunnel)**: egy privát "cső" a gépedtől a Cloudflare-ig (egy cég, amely az internet egy részét működteti).
  A látogatók a Cloudflare-hez fordulnak, a Cloudflare a csövön át továbbítja a kérést a gépedhez. Mivel a gép hív ki a
  Cloudflare felé, senkinek sem kell tudnia behívni a gépbe.
- **Biztonsági mentés**: az adatok másolata, hogy egy tévedést vagy egy sikertelen frissítést vissza lehessen vonni.
  A Lineup mentései hogyan működnek, és mi ellen **nem** védenek, a [8. részben](#8-biztonsági-mentések) olvasható.
  Kérjük, olvasd el, mielőtt valódi adatot viszel fel.

**Még egy dolog, mielőtt valódi emberek használják.** A Lineup saját üzemeltetése **nem** mentesít az
adatvédelmi törvény (GDPR) alól. Aki üzemelteti, az felel az emberek adataiért. Amíg a [[Privacy and Security]] oldal
önüzemeltetett példányokról szóló részében lévő adatvédelmi ellenőrzőlista nincs végigvíve, csak kitalált neveket és
adatokat használj.

**Megjegyzés a szóhasználatról.** A Cloudflare és a Google gyakran változtatja a menüit, ezért ebben az útmutatóban
nincsenek képernyőképek. A gombokat úgy nevezzük meg, ahogy az írás idején hívják őket; ha nem találod, **keresd a
legközelebbi megnevezést**.

**Az értékeket egyetlen privát helyen gyűjtsd.** Az alábbi lépésekben összegyűjtesz néhány értéket (egy címet, egy
tokent, egy kliensazonosítót). Ezeket egy jegyzetben tartsd a **saját számítógépeden**, soha ne e-mailben vagy
csevegőben. Ha sima szövegfájlt használsz, tedd privátá: a saját számítógépeden, terminálban futtasd ezt:
`mkdir -p ~/.config/lineup && touch ~/.config/lineup/selfhost.env && chmod 600 ~/.config/lineup/selfhost.env`.
Egy jelszókezelő ugyanilyen jó.

---

## 2. Mielőtt hozzákezdesz

Hat dolognak kell készen állnia a telepítés előtt. Nem nagyon függnek egymástól, bármilyen sorrendben megcsinálhatod
őket, de mindet meg kell csinálni.

### 2.1 A gép ellenőrzése

A gépnek folyamatosan be kell lennie kapcsolva, telepített Dockerrel, legalább 2 GB memóriával (a 4 GB kényelmes)
és legalább 10 GB szabad hellyel.

**Teendő.** Nyiss egy terminált **a gépen**. NAS-on keresd a beállításokban a "Terminal" vagy "SSH" pontot (ha kell,
kapcsold be), és csatlakozz a számítógépedről, vagy használd a gyártó terminálalkalmazását. Utána másold be ezt a sort,
és nyomj Entert:

```bash
uname -m; grep MemTotal /proc/meminfo; df -h .; docker --version; docker compose version
```

**Ezt kell látnod.** Nagyjából öt csoport sort:

- `x86_64` vagy `aarch64` (a processzor fajtája; mindkettő jó),
- `MemTotal:` után legalább 2000000 szám (ez kilobájt: 2 GB),
- egy táblázat, amelyben a mappád **Avail** oszlopa legalább 10G,
- `Docker version 2x.x.x`,
- `Docker Compose version v2.20` vagy újabb.

**Ha nem.** A `docker: command not found` azt jelenti, hogy a Docker nincs telepítve: NAS-on telepítsd a gyártó
alkalmazásközpontjából (keresd a "Docker" vagy "Container Manager" nevet). Ha 2 GB-nál kevesebb a memória, vagy a
Docker nem telepíthető, ez a gép nem alkalmas. Itt állj meg, és kérj segítséget.

### 2.2 Ki gondozza?

Valakinek le kell futtatnia a frissítéseket, és ha kell, a visszaállítást. Válaszd ki most ezt a személyt. A frissítések
nem maguktól történnek (ez szándékos: kívülről semmi nem tud a gépbe csatlakozni), ezért a gép gondozójának időnként
lefuttatnia egy parancsot.

**Teendő.** Írd fel, ki az. Ha ő nem a géphez ülve dolgozik, hanem a saját számítógépéről, akkor távolról is meg kell
tudnia nyitni egy terminált a gépen (SSH). A kipróbálás nem kötelező: a saját számítógépén terminálban futtassa ezt:
`ssh felhasznalo@gepneve docker ps` (a valódi felhasználónévvel és gépnévvel), és nézze meg, hogy megjelenik-e a
konténerek táblázata, akár üresen is.

**Ezt kell látnod.** Egy `CONTAINER ID` kezdetű fejlécsor, akkor is, ha alatta nincs semmi.

**Ha nem.** `Permission denied` vagy `Connection refused`: az SSH ki van kapcsolva, vagy a felhasználó téves. Ezt hagyd
ki, mindent meg lehet csinálni magán a gépen is.

### 2.3 A domain megvétele és hozzáadása a Cloudflare-hez

**Teendő.**

1. Hozz létre egy [Cloudflare](https://dash.cloudflare.com/sign-up)-fiókot. Ha van közös vagy szerepkör alapú postaládátok
   (nem egy ember privát levelezése), azt add meg. A profilbeállításokban kapcsold be a **kétlépcsős azonosítást**: ez a
   fiók irányítja a gépbe vezető utat.
2. Vegyél egy domaint, nagyjából 10 euró évente. A legegyszerűbb a **Cloudflare Registrar**, mert máshol nincs
   dolgod. Ha nem árulja a kívánt végződést, vedd meg máshol, add hozzá a Cloudflare-hez (keresd az "Add a domain"
   gombot), és az eladónál írd át a névszervereket (nameserver) arra a kettőre, amelyet a Cloudflare mutat. Olyan nevet
   válassz, amelyből nem derül ki, hol van a gép.
3. Írd a privát jegyzetedbe: `PUBLIC_URL=https://lineup.example.com`, a saját domainaddal és **per jel nélkül a végén**.

**Ezt kell látnod.** A domained a Cloudflare irányítópultján (dashboard) **Active** állapotban.

**Ha nem.** Ha máshol vett domainnél "Pending nameserver update" áll, az eladónál a névszerverek átírása még nem
lépett életbe. Ez akár egy napig is eltarthat, közben menj tovább a többi lépéssel.

### 2.4 Az alagút létrehozása

**Teendő.**

1. A Cloudflare irányítópultján nyisd meg a **Zero Trust** részt, és válaszd az ingyenes (**Free**) csomagot. Egyesek
   szerint az ingyenes csomagnál is bankkártyát kér. Ha így van, az ingyenes csomagon nem szabad semmit terhelnie:
   mielőtt jóváhagyod, ellenőrizd az oldalon.
2. Menj ide: **Networks → Tunnels → Create a tunnel**, válaszd a **Cloudflared** típust, és nevezd el `lineup`-nak.
3. Az oldal egy telepítő parancsot mutat, amelyben a `--token` után egy hosszú szöveg áll. Másold ki **csak ezt a hosszú
   szöveget** (a tokent), és írd a privát jegyzetedbe így: `TUNNEL_TOKEN=<a hosszú szöveg>`. **Ne futtasd le azt a
   parancsot**: az alagutat a Lineup indítja el magától.
4. Adj hozzá egy **Public hostname**-et: a domained, **aldomain és útvonal nélkül**. A szolgáltatás típusa legyen `HTTP`,
   az URL pedig `web:8080`.
5. Nyisd meg magának a domainnek a beállításait, és kapcsold **ki** ezt a négyet, mert szkripteket szúrnak az oldalakba,
   vagy blokkolják az alkalmazás saját forgalmát: **Web Analytics**, **Rocket Loader**, **Email Address Obfuscation**
   és **Bot Fight Mode**. Kapcsold **be** az **Always Use HTTPS** beállítást.

**Ezt kell látnod.** Az alagút a listában **Inactive** vagy "Down" állapottal. Ez rendben van: a telepítésig semmi nem
csatlakozik hozzá.

**Ha nem.** Ha nem találod a "Zero Trust" menüt, nézd meg a bal oldali menüben a "Networks" vagy "Tunnels" pontot, vagy
keress rá az irányítópulton a "tunnel" szóra.

**Az analitika és a követés maradjon kikapcsolva.** A Lineup maga nem használ sütiket, analitikát, nyomkövetőket,
külső betűtípusokat vagy külső szkripteket, és ez szándékos: így nincs szükség hozzájárulást kérő sávokra, és a
látogatások privátak maradnak. Kérjük, hogy ez így maradjon. Ne kapcsold be a Cloudflare Web Analyticset (vagy bármilyen
hasonló "insights" vagy "analytics" funkciót), ne tegyél Google Analyticset vagy bármilyen követőszkriptet az oldalra, és
ne használj olyan Cloudflare-funkciót, amely átírja az oldalakat (Rocket Loader, Email Address Obfuscation, Zaraz). Ha
egy irányítópult felajánlja, hogy "segítségképpen" bekapcsol valamelyiket, a válasz: nem.

### 2.5 A Google-bejelentkezés létrehozása

Az emberek Google-lal jelentkeznek be. A Google-nek tudnia kell az oldaladról, és megadhatod, mely fiókok használhatják.

Ehhez csinálj egy **új** Google Cloud-projektet, ne olyat használj, amelyet másra használsz. Az engedélyezett emberek
listája a projekthez tartozik.

**Teendő.**

1. Nyisd meg a [Google Cloud konzolt](https://console.cloud.google.com/), és hozz létre egy **New project**-et, például
   `lineup-selfhost` néven.
2. Keresd a **Google Auth Platform → Audience** részt. Válaszd az **External** típust és a **Testing** közzétételi
   állapotot. A **Test users** alatt vedd fel mindenkit, aki bejelentkezhet, a Google e-mail-címével. Csak ezek a
   fiókok léphetnek be.
3. Keresd a **Data access** részt, és ellenőrizd, hogy csak az `openid`, az `email` és a `profile` van kijelölve.
4. Keresd a **Clients → Create client** részt, és válaszd a **Web application** típust. Add meg:
   - Authorized JavaScript origin: `https://lineup.example.com`
   - Authorized redirect URI: `https://lineup.example.com/auth/v1/callback`

   (a saját domainaddal, pontosan beírva; az elsőnek a végén nincs per jel).
5. A Google ezután megmutat egy kliensazonosítót (client id) és egy kliens-titkot (client secret). Írd őket a privát
   jegyzetedbe így: `GOOGLE_CLIENT_ID=<az azonosító>` és `GOOGLE_SECRET=<a titok>`.

**Ezt kell látnod.** A klienst a listában, az embereidet pedig a Test users alatt.

**Ha nem.** Ha a konzol előbb egy "consent screen" vagy "branding" beállítását kéri, add meg az alkalmazás nevét (például
`Lineup`) és a saját e-mail-címedet támogatási kapcsolatként, majd menj vissza a 4. lépéshez.

### 2.6 A mentések korlátainak elolvasása és elfogadása

Itt nincs mit kattintani, de ez a te döntésed. Olvasd el, és gondold végig, hogy elfogadod-e:

> A biztonsági mentések minden éjjel lefutnak, és 30 napig megmaradnak, ugyanezen a gépen lévő mappában. **Nincsenek
> titkosítva**, és bárki elolvashatja őket, aki hozzáfér ehhez a géphez. Tévedések és sikertelen frissítések ellen
> védenek. **Ha ez a gép elvész vagy tönkremegy, minden adat elvész**, hacsak valaki kézzel át nem másolta máshová a
> mentési mappát. Mentsd el a `.env` fájlt is egy biztonságos, privát helyre: nélküle egy új gépen végzett
> visszaállításnál mindenki bejelentkezését és az adatbázis jelszavait újra be kell állítani.

Ha a gépnek van második lemeze, vagy van egy mappád egy másik eszközön (hálózati megosztás), válassz ott egy mappát a
mentéseknek, és írd a privát jegyzetedbe: `BACKUP_DIR=/ennek/a/mappanak/az/utja`. Ha nem, a mentések a Lineup mellett
egy `backups` nevű mappába kerülnek, ami az induláshoz megfelel.

**Ezt kell látnod.** Semmit: ez döntés, nem művelet. A telepítő ugyanezt a szöveget mutatja, és egy szó beírásával kell
megerősítened.

**Ha nem.** Ha ezek a korlátok nem elfogadhatók számodra, itt állj meg. A mentési mappa kézi, máshová másolása (8. rész)
sokkal biztonságosabbá teszi.

**Készen vagy?** A privát jegyzetedben ennek kell lennie: `PUBLIC_URL`, `TUNNEL_TOKEN`, `GOOGLE_CLIENT_ID`,
`GOOGLE_SECRET`, és ha választottál, `BACKUP_DIR`.

---

## 3. Telepítés

Ezt **a gépen** csinálod, terminálban.

### 3.1 A Lineup felvitele a gépre

**Teendő.** Nyisd meg a [kiadások oldalát](https://github.com/LasterBergamot/lineup/releases), keresd meg a legújabb
kiadást, és jegyezd meg a verziószámát, például `v0.2.0`. Aztán a terminálban futtasd egymás után ezt a négy parancsot,
mindkét `v0.2.0`-t kicserélve erre a verzióra:

```bash
curl -LO https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz
curl -LO https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz.sha256
sha256sum -c selfhost-v0.2.0.tar.gz.sha256
tar -xzf selfhost-v0.2.0.tar.gz
```

**Ezt kell látnod.** A harmadik parancs után: `selfhost-v0.2.0.tar.gz: OK`. Ez azt jelenti, hogy a letöltés teljes és
változatlan. A negyedik parancs nem ír ki semmit, és létrehoz egy `selfhost` nevű mappát.

**Ha nem.** A `FAILED` azt jelenti, hogy a letöltés sérült vagy megváltoztatták: töröld a két fájlt, kezdd elölről, és ne
menj tovább. `curl: command not found`: a `curl -LO` helyett használd a `wget` parancsot. "Not found" oldal: rossz a
verziószám, vagy abban a kiadásban még nincs `selfhost` fájl; próbáld az előző kiadást.

### 3.2 A gép ismételt ellenőrzése

**Teendő.**

```bash
cd selfhost
./lineup.sh doctor
```

**Ezt kell látnod.** Ellenőrzések listáját, mindegyik mellett OK, figyelmeztetés vagy hiba jelzéssel. A figyelmeztetést
(például kevés szabad hely) érdemes elolvasni, de nem állít meg. Minden hibához tartozik egy sor, amely megmondja, hogyan
kell kijavítani.

**Ha nem.** `Permission denied`: futtasd a `chmod +x lineup.sh` parancsot, és próbáld újra. Minden **hibát** javíts ki,
mielőtt továbbmész.

### 3.3 A telepítő futtatása

**Teendő.** Legyen előtted a privát jegyzeted, és futtasd:

```bash
./lineup.sh install
```

A telepítő sorban kérdez: a nyilvános cím (`https://lineup.example.com`, `https://`-sel kell kezdődnie, útvonal nélkül),
az alagút tokenje, a Google kliensazonosítója, a Google kliens-titka és a mentési mappa. Mindegyiket másold be a
jegyzetedből. A titoknál **semmi nem jelenik meg beillesztés közben**: ez normális, szándékosan rejtett. Ezután megmutatja
a 2.6 pontbeli mentési korlátokat, és megkér, hogy írd be: `IGEN` (angolul `YES`). A telepítő alapból magyarul szól;
ha felajánlja a nyelv kiválasztását, a magyart válaszd.

**Ezt kell látnod.** A telepítő létrehozza a saját jelszavait (soha nem mutatja meg őket), mindent elindít, végül
üzenetet ad arról, hogy a Lineup fut, megmondja a címet, és emlékeztet arra, mit kell elmentened. Az első alkalommal pár
percig tart, mert letölti a program részeit.

**Ha nem.**

- "Már van `.env` fájl": ez biztonsági ellenőrzés. A telepítő nem írja felül a meglévő beállításokat, mert az
  kizárná a Lineupot a saját adatbázisából. Ha ez friss telepítés, korábban már lefuttattad; használd a 7. részt
  (frissítés).
- Egy értéket elutasít: olvasd el az üzenetet. Általában az `https://` hiányzik a cím elejéről, vagy per jel van a végén.
- A telepítő üzenettel leáll: olvasd el, javítsd, amit mond, és futtasd újra a `./lineup.sh install` parancsot, kivéve, ha
  már létrehozta a `.env` fájlt, mert akkor az üzenet megmondja, mit tegyél.

### 3.4 A `.env` fájl elmentése

A telepítő létrehozott egy `.env` nevű fájlt abban a mappában, ahol vagy. Ebben van minden jelszó, amelyre a Lineupnak
szüksége van. Máshol **nincs** eltárolva.

**Teendő.** Másold ezt a fájlt egy biztonságos, privát helyre, amely **nem ezen a gépen van**: egy fájlokat is tároló
jelszókezelőbe vagy egy titkosított pendrive-ra. A neve ponttal kezdődik, ezért a fájlkezelők elrejtik: keresd a "rejtett
fájlok megjelenítése" lehetőséget. Ne küldd el e-mailben, és ne tedd megosztott mappába.

**Ezt kell látnod.** A fájlt biztonságosan eltárolva, máshol.

**Ha nem.** Ha nem találod, a terminálban futtasd az `ls -a` parancsot a Lineup mappájában: a `.env` nevű fájl ott lesz a
listában.

---

## 4. Működik-e?

**Teendő.**

1. A terminálban futtasd: `./lineup.sh status`.
2. Bármelyik számítógépen vagy telefonon nyisd meg a `https://lineup.example.com` címet (a saját domainaddal).
3. Nyomd meg a bejelentkezés gombot, és jelentkezz be egy olyan Google-fiókkal, amely a tesztfelhasználók listáján van.

**Ezt kell látnod.**

1. Konténerek listáját, mind futó állapotban, egy sort arról, hogy az alkalmazás egészséges, az utolsó mentés korát
   (az első napon még nincs), a szabad helyet és a jelenlegi verziót.
2. A Lineup nyitóoldalát.
3. Bejelentkezés után visszakerülsz a Lineupba, és létrehozhatsz egy csapatot.

**Ha nem.**

- A státusz hibát mutat: olvasd el a sort, majd lásd a [10. részt](#10-ha-valami-nem-működik).
- Az oldal nem nyílik meg: várj két percet (az alagútnak kell egy kis idő), majd lásd a 10. részt, "Az oldal nem érhető
  el".
- A Google **access blocked** üzenetet ad: a fiók nincs a tesztfelhasználók listáján. Lásd az 5. részt.

---

## 5. Személy hozzáadása vagy törlése

Azt, hogy ki léphet be, a Google tesztfelhasználói listája dönti el, nem a Lineup.

**Teendő.**

1. Nyisd meg a [Google Cloud konzolt](https://console.cloud.google.com/), és válaszd ki a Lineup-projektedet.
2. Menj ide: **Google Auth Platform → Audience → Test users**.
3. Személy hozzáadásához válaszd az **Add users** gombot, és írd be a Google e-mail-címét. Törléséhez vedd ki a címét a
   listából. Mentsd.
4. Amint valaki be tud jelentkezni, egy meghívó linkkel csatlakozik egy csapathoz a Lineupban; a linket a csapat egy
   tagja készíti az alkalmazásban.

**Ezt kell látnod.** Az új címet a listában. A személy innentől be tud jelentkezni.

**Ha nem.** Ha a személy még mindig **access blocked** üzenetet kap, nézd meg, hogy pontosan azt a Google-fiókot használja-e
(nem egy másikat, amely ugyanabban a böngészőben be van jelentkezve), és várj egy percet.

Ha valakit kiveszel a listából, többé nem tud bejelentkezni, de az adatai nem törlődnek a Lineupból. Ha valaki az adatai
törlését vagy kiadását kéri, az külön feladat külön szabályokkal: lásd [[Privacy and Security]].

---

## 6. Mindennapok

Naponta semmit nem kell csinálni. A mentések éjjel maguktól lefutnak, és a Lineup magától újraindul, ha a gép újraindul.

**Havonta egyszer** nyiss egy terminált a gépen, menj a Lineup mappájába, és futtasd:

```bash
./lineup.sh status
```

Három dolgot nézz meg: az alkalmazás egészséges-e, az utolsó mentés **másfél napnál fiatalabb**-e, és van-e még szabad
hely. A státusz azt is megmondja, hogy van-e újabb Lineup-verzió. A frissítések nem települnek maguktól: ha van újabb
verzió, ütemezz be egy frissítést (7. rész).

**Ezt kell látnod.** Egészséges alkalmazást és friss mentést.

**Ha nem.** Lásd a [10. részt](#10-ha-valami-nem-működik).

---

## 7. Frissítés

**Teendő.** Válassz csendes időt (az alkalmazás rövid időre elérhetetlen), nyiss egy terminált a gépen, menj a Lineup
mappájába, és futtasd:

```bash
./lineup.sh update
```

Magától elvégzi ezeket, és közben tájékoztat: megkeresi a legújabb verziót, letölti, és ellenőrzi, hogy sértetlen-e,
**előbb mentést készít** (és leáll, ha a mentés nem sikerül, így soha nincs frissítés friss mentés nélkül), telepíti az új
verziót, és ellenőrzi, hogy működik-e.

Ha egy adott verzióra akarsz lépni, add meg: `./lineup.sh update --version v0.2.0`.

**Ezt kell látnod.** Üzenetet arról, hogy a Lineup az új verzión fut, és egészséges. Utána futtasd a `./lineup.sh status`
parancsot.

**Ha nem.** Ha a frissítés nem sikerül, a szkript pontosan megmondja, mi történt. Két eset van:

- Azt írja, hogy a frissítést **visszavonta, és semmi nem veszett el**: a Lineup újra a régi verzión fut. Várj egy napot,
  vagy kérj segítséget az üzenettel.
- Azt írja, hogy az **adatbázis megváltozott**: nem találgat. Kövesd az üzenetben lévő utasítást: megnevez egy
  visszaállító parancsot, amely a frissítés előtti mentésre áll vissza (9. rész).

Ne próbálkozz saját megoldással. Ha egyik üzenet sem jelenik meg, kérj segítséget.

A fejlesztők ugyanezt a frissítést a saját számítógépükről is el tudják indítani; lásd [[Self-Hosting Reference]].

---

## 8. Biztonsági mentések

Ezt a részt olvasd el figyelmesen. Megmondja, mire jók a mentések, és mire nem.

> A biztonsági mentések minden éjjel lefutnak, és 30 napig megmaradnak, ugyanezen a gépen lévő mappában. **Nincsenek
> titkosítva**, és bárki elolvashatja őket, aki hozzáfér ehhez a géphez. Tévedések és sikertelen frissítések ellen
> védenek. **Ha ez a gép elvész vagy tönkremegy, minden adat elvész**, hacsak valaki kézzel át nem másolta máshová a
> mentési mappát. Mentsd el a `.env` fájlt is egy biztonságos, privát helyre: nélküle egy új gépen végzett
> visszaállításnál mindenki bejelentkezését és az adatbázis jelszavait újra be kell állítani.

Egyszerűen: a mentések akkor segítenek, ha valaki tévedésből töröl valamit, vagy egy frissítés félresikerül. Akkor nem
segítenek, ha a gépet ellopják, kigyullad, vagy a lemeze tönkremegy, mert a mentések ugyanazon a gépen vannak. Ennek
kivédésére **másold át kézzel a mentési mappát máshová** időnként, például havonta egyszer.

Két jó, ha tudott részlet. A mentésekben nincsenek benne az emberek bejelentkezési munkamenetei, ezért visszaállítás után
mindenkinek újra be kell jelentkeznie, és egy ellopott mentéssel nem lehet átvenni egy bejelentkezett munkamenetet. A 30
napnál régebbi mentések maguktól törlődnek.

**Mentés készítése most.** Futtasd: `./lineup.sh backup`. Kiírja a létrehozott fájlokat és a méretüket.

**A mappa kézi másolása máshová.**

1. Keresd meg a mappát: a jegyzetedben lévő `BACKUP_DIR`, vagy a Lineup mappájában a `backups` nevű mappa.
2. Másold az egész mappát egy pendrive-ra, egy másik számítógépre vagy egy másik eszközre. NAS-on ez általában megoldható a
   fájlkezelővel (másold a mappát egy másik megosztásra vagy lemezre). SSH-val egy másik számítógépről az egyik mód:
   `scp -r felhasznalo@gepneve:/a/mentesek/utja ./lineup-mentesek` (a valódi felhasználóval, géppel és úttal). A mentések
   nincsenek titkosítva, ezért a másolatot is privát helyen tartsd.
3. A mappában éjszakánként két fájlt látsz, például `lineup-2026-11-04.dump` és `auth-2026-11-04.dump` néven (az egyik az
   adatoké, a másik a bejelentkezési fiókoké), meg egy kis `last-success` fájlt, amely az utolsó sikeres mentés idejét
   tartalmazza. Mindig mindet másold.

**Ezt kell látnod.** A másolatot az eredeti mellett, ugyanazokkal a fájlokkal.

**Ha nem.** Ha a másolat sokkal kisebb az eredetinél, vagy fájlok hiányoznak, a másolás megszakadt: csináld újra.

---

## 9. Visszaállítás

A visszaállítás az adatokat egy korábbi éjszaka állapotára viszi vissza. Akkor használd, ha olyan tévedés történt, amelyet
másképp nem tudsz helyrehozni, vagy ha a frissítés üzenete azt kéri.

**Mielőtt megcsinálod, tudd:** minden, amit az adott dátum **után** vittek be, **elvész**, és **mindenkinek újra be kell
jelentkeznie**.

**Teendő.** A gépen, terminálban, a Lineup mappájában:

```bash
./lineup.sh restore
```

Kilistázza azokat a dátumokat, amelyekhez van mentés. Közvetlenül egy dátum kiválasztásához:
`./lineup.sh restore --date 2026-11-03` (a listában szereplő dátumot használd). Még egyszer figyelmeztet, és megkér, hogy
írd be: `VISSZAALLIT` (angolul `RESTORE`). Ezután **először biztonsági mentést készít a jelenlegi állapotról** (így még egy
téves visszaállítás is visszavonható), leállítja az alkalmazást, visszaállítja az adatokat, mindent elindít, és ellenőrzi,
hogy működik-e.

**Ezt kell látnod.** Üzenetet arról, hogy a visszaállítás befejeződött, és a Lineup egészséges. Nyisd meg a címet, és
jelentkezz be újra.

**Ha nem.** Ha a visszaállítás üzenettel leáll, kövesd az üzenetet. A biztonsági mentés miatt semmi nem vész el, ha
újrapróbálod. Ha az egész gép elveszett, az új gépen való visszaállításhoz kell a mentési mappa **és** az elmentett
`.env` fájl (3.4 pont): ehhez kérj segítséget.

---

## 10. Ha valami nem működik

| Amit látsz | Mit tegyél | Mikor kérj segítséget |
|---|---|---|
| **Az oldal nem érhető el** (nem nyílik meg) | Be van-e kapcsolva a gép, és kapcsolódik-e a hálózathoz? Futtasd a `./lineup.sh status` parancsot: futnak-e a konténerek? A Cloudflare irányítópultján nyisd meg a **Networks → Tunnels** részt: a `lineup` egészségesnek vagy csatlakozottnak látszik-e? Ha nem, indítsd újra a gépet (a Lineup magától elindul), és várj pár percet | A gép be van kapcsolva, minden fut, az alagút csatlakozik, mégsem nyílik meg az oldal; vagy az alagút tokenjét megváltoztatták |
| **A bejelentkezés "access blocked" üzenetet ad** (vagy "this app is not verified", továbblépés nélkül) | A fiók nincs a tesztfelhasználók listáján. Add hozzá (5. rész) | A fiók rajta van a listán, és pár perc után is hibás |
| **A Google `redirect_uri_mismatch` hibát mutat** | A Google Cloud konzolban, a **Clients** alatt ellenőrizd, hogy az átirányítási URI pontosan `https://lineup.example.com/auth/v1/callback`, a te domaineddal (2.5 pont) | Pontosan egyezik, és mégis hibás |
| **A bejelentkezés sikerül, de üres vagy hibás oldalra jutsz** | Futtasd a `./lineup.sh status` parancsot. Ha egy konténer nem egészséges, várj egy percet, és nézd meg újra | Öt perc után is egészségtelen marad |
| **A `status` szerint az utolsó mentés másfél napnál régebbi** | Futtasd a `./lineup.sh backup` parancsot, és olvasd el, mit ír. A szabad helyet a `./lineup.sh status` mutatja | A mentés nem sikerül, vagy a lemez majdnem tele van |
| **A lemez majdnem tele van** | Szabadíts fel helyet a gépen, vagy vidd máshová a régi mentéseket (előbb másold, aztán töröld) | Nem tudod, mit biztonságos törölni: a Lineup mappáját és a `.env` fájlt ne töröld |
| **Egy frissítés nem sikerült** | Pontosan azt tedd, amit az üzenet mond (visszavonva, vagy visszaállító parancs) | Az üzenet nem jelent meg, vagy nem érted |
| **Egy PDF nem tölt le, vagy sokáig tart** | Várj egy percet, és próbáld újra. Nagyon ritkán előfordul, hogy sokan egyszerre készítenek PDF-et | Folyamatosan hibázik |
| **Visszaállítás után senki nincs bejelentkezve** | Ez várható. Mindenki újra bejelentkezik | Újbóli bejelentkezés után sem működik |

**Segítségkérés.** Mondd el, mit csináltál, mit láttál, és másold be a pontos üzenetet. Soha ne küldd el senkinek a `.env`
fájlodat, az alagút tokenjét vagy a Google kliens-titkát, és ne tedd ki őket nyilvános helyre: teljes hozzáférést adnak.
Ha azt gyanítod, hogy valamelyik kiszivárgott, az adatvédelmi incidens: kövesd a [[Breach Runbook]] oldalt.
