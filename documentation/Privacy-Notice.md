# Privacy Notice

The privacy notices for Lineup, in English and Hungarian. They are written from the facts on
[[Privacy and Security]] (the data inventory): if a fact there changes, change the notices in the same
PR. The web app will serve these texts on a privacy page linked from the sign-in page and the footer
(#97); until then this file is the source.

`[…]` marks a placeholder the operator fills in (see *Facts the operator must fill in* on
[[Privacy and Security]]). Not legal advice: the Hungarian text should be read once by a native
speaker with legal knowledge (⚖).

Contents:

1. [Notice for account holders, English (Art. 13)](#1-notice-for-account-holders-english-art-13)
2. [Tájékoztató felhasználóknak, magyarul (13. cikk)](#2-tájékoztató-felhasználóknak-magyarul-13-cikk)
3. [Template for clubs to give to players, staff and parents, English (Art. 14)](#3-template-for-clubs-english-art-14)
4. [Minta sportszervezeteknek játékosok, stábtagok és szülők tájékoztatására, magyarul (14. cikk)](#4-minta-sportszervezeteknek-magyarul-14-cikk)

---

## 1. Notice for account holders, English (Art. 13)

**Who we are.** Lineup is run by [OPERATOR NAME], [OPERATOR ADDRESS] ("we"). Contact for anything in
this notice: [PRIVACY E-MAIL]. We have not appointed a data protection officer.

**Two roles.** For your **account** (signing in, your team memberships) we decide why and how your data
is used: we are the controller. For the **players, staff and lineups** that a club enters, the club is
the controller and we only process the data for it, on its instructions. If you are a player or
parent, see the notice from your club (section 3) and send requests to the club.

**What we use and why.**

| Data | Why | Legal basis (GDPR) |
|---|---|---|
| From your Google account, through our sign-in provider Supabase: e-mail address, name, profile picture, account id | To let you sign in and to recognise you | Art. 6(1)(b): providing the service you signed up for |
| A random user id, your role in a team, when you joined, the teams and lineups you created | To decide what you may see and change, and to keep an audit trail | Art. 6(1)(b) and (f): our interest in running the service securely |
| Your name, if you create an invite link | To show "invited by …" on the join page | Art. 6(1)(f) |
| Your IP address and your user id, in memory only, for 60 seconds | To stop abuse (rate limits). Never written down | Art. 6(1)(f) |

We do not use your data for advertising, profiling or automated decisions, and we do not sell it.

**Who receives it.** Our service providers (processors), under contracts that bind them to our
instructions: Supabase (database and sign-in, Ireland), Fly.io (runs the API, Amsterdam) and
Cloudflare (serves the web app). Google is a separate controller for your Google account; its
privacy policy applies to the sign-in. We may also use Sentry for error reports in the EU, only
after we have updated this notice. Some providers are US companies: transfers rely on the EU–US
Data Privacy Framework or the standard contractual clauses. The current list is on the page
*Privacy and Security*.

**Browser storage.** Lineup sets no cookies and uses no analytics, trackers or third-party fonts.
It stores a few entries in your browser, all strictly necessary for what you asked for, so no consent
is needed:

- the Supabase sign-in session (`sb-…`, localStorage): keeps you signed in until you sign out,
- `lineup-lang` (localStorage): your chosen language, written only when you click the language switch,
- `lineup-theme` (localStorage): light or dark,
- `lineup-return-to` (sessionStorage): the page to return to after signing in, removed afterwards.

**How long.** We keep your account until you ask us to delete it or you remove yourself from all teams
and ask for deletion. Invite links are deleted a week after they expire. Rate-limit counters last 60
seconds. Generated lineup files are never stored. Backups of the database, if the provider makes any,
can keep deleted data for up to 30 days.

**Your rights.** You can ask us for access to your data, correction, erasure, restriction, a portable
copy, and you can object to processing based on legitimate interest (Arts. 15–21 GDPR). Write to
[PRIVACY E-MAIL]; we answer within one month. If you are under 18, you or your parent can make the
request. Sign-up is for people aged **16 or over**.

**Complaints.** You can complain to the Hungarian supervisory authority: Nemzeti Adatvédelmi és
Információszabadság Hatóság (NAIH), 1055 Budapest, Falk Miksa utca 9-11., www.naih.hu,
ugyfelszolgalat@naih.hu. You can also go to court.

**Providing data.** Without your Google sign-in data you cannot use the service. Nothing else you give
is required by law or contract.

*Last updated: [DATE].*

---

## 2. Tájékoztató felhasználóknak, magyarul (13. cikk)

**Ki vagyunk.** A Lineupot [OPERATOR NAME], [OPERATOR ADDRESS] ("mi") üzemelteti. Kapcsolat az ebben a
tájékoztatóban szereplő bármely kérdésben: [PRIVACY E-MAIL]. Adatvédelmi tisztviselőt nem neveztünk ki.

**Két szerepünk van.** A **fiókoddal** (bejelentkezés, csapattagságok) kapcsolatban mi döntünk az adatok
céljáról és módjáról: mi vagyunk az adatkezelő. Az egyesületek által felvitt **játékosok, stábtagok és
összeállítások** adatainak az egyesület az adatkezelője, mi csak az ő megbízásából és utasításai szerint
dolgozzuk fel azokat (adatfeldolgozó). Ha játékos vagy szülő vagy, olvasd el az egyesületed tájékoztatóját
(4. rész), és a kéréseidet az egyesületnek küldd.

**Milyen adatot miért kezelünk.**

| Adat | Miért | Jogalap (GDPR) |
|---|---|---|
| A Google-fiókodból, a bejelentkeztető szolgáltatónk (Supabase) útján: e-mail-cím, név, profilkép, fiókazonosító | Hogy be tudj jelentkezni és felismerjünk | 6. cikk (1) b): a kért szolgáltatás nyújtása |
| Véletlenszerű felhasználói azonosító, a szereped egy csapatban, a csatlakozás ideje, az általad létrehozott csapatok és összeállítások | Hogy eldöntsük, mit láthatsz és módosíthatsz, és hogy legyen nyomon követés | 6. cikk (1) b) és f): a szolgáltatás biztonságos üzemeltetéséhez fűződő jogos érdekünk |
| A neved, ha meghívó linket hozol létre | Hogy a csatlakozó oldalon megjelenjen, ki hívott meg | 6. cikk (1) f) |
| Az IP-címed és a felhasználói azonosítód, csak a memóriában, 60 másodpercig | A visszaélések megakadályozása (kérésszám-korlát). Soha nem íródik ki | 6. cikk (1) f) |

Az adataidat nem használjuk reklámra, profilalkotásra vagy automatizált döntésre, és nem adjuk el.

**Kik kapják meg.** A szolgáltatóink (adatfeldolgozók), akiket szerződés köt az utasításainkhoz: a
Supabase (adatbázis és bejelentkezés, Írország), a Fly.io (az API futtatása, Amszterdam) és a
Cloudflare (a webalkalmazás kiszolgálása). A Google önálló adatkezelő a Google-fiókod tekintetében;
a bejelentkezésre az ő adatvédelmi tájékoztatója vonatkozik. Hibajelentésekhez később használhatjuk a
Sentryt is, EU-régióban, de csak e tájékoztató frissítése után. Egyes szolgáltatók amerikai cégek: az
adattovábbítás az EU–USA adatvédelmi keretrendszerre (DPF) vagy általános szerződési feltételekre
(SCC) épül. A mindenkori lista az *Privacy and Security* oldalon található.

**Böngészőtárhely.** A Lineup nem használ sütiket, analitikát, nyomkövetőt vagy külső betűtípusokat.
Néhány bejegyzést a böngésződben tárol, amelyek mind elengedhetetlenek az általad kért szolgáltatáshoz,
ezért nem kell hozzájárulás:

- a Supabase bejelentkezési munkamenet (`sb-…`, localStorage): kijelentkezésig bejelentkezve tart,
- `lineup-lang` (localStorage): a választott nyelv, csak a nyelvváltó kattintásakor íródik,
- `lineup-theme` (localStorage): világos vagy sötét téma,
- `lineup-return-to` (sessionStorage): a bejelentkezés után visszatérési oldal, utána törlődik.

**Meddig.** A fiókodat addig tartjuk meg, amíg kéred a törlését, vagy kilépsz minden csapatból és kéred
a törlést. A meghívó linkek a lejáratuk után egy héttel törlődnek. A kérésszám-számlálók 60 másodpercig
élnek. A generált összeállítás-fájlokat soha nem tároljuk. Az adatbázis biztonsági mentései, ha a
szolgáltató készít ilyet, a törölt adatot legfeljebb 30 napig őrizhetik.

**A jogaid.** Kérhetsz hozzáférést az adataidhoz, helyesbítést, törlést, korlátozást, adathordozhatóságot,
és tiltakozhatsz a jogos érdeken alapuló kezelés ellen (GDPR 15–21. cikk). Írj a [PRIVACY E-MAIL]
címre; egy hónapon belül válaszolunk. 18 év alatt te vagy a szülőd is élhet a joggal. A regisztráció
**16 éves kortól** lehetséges.

**Panasz.** Panasszal fordulhatsz a Nemzeti Adatvédelmi és Információszabadság Hatósághoz (NAIH), 1055
Budapest, Falk Miksa utca 9-11., www.naih.hu, ugyfelszolgalat@naih.hu. Bírósághoz is fordulhatsz.

**Az adatszolgáltatás.** A Google-bejelentkezési adatok nélkül nem tudod használni a szolgáltatást.
Más adatot jogszabály vagy szerződés nem ír elő.

*Utolsó frissítés: [DÁTUM].*

---

## 3. Template for clubs, English (Art. 14)

*For the club to adapt and give to players, staff and, for minors, their parents. The club is the
controller; Lineup is its processor. Put your own club name and contact in the brackets. Players do
not sign in to Lineup and do not give us the data themselves, so this is the Art. 14 information that
must reach them (within one month, and at the latest at the first contact).*

**Privacy information for players, staff and parents of [CLUB NAME]**

[CLUB NAME], [CLUB ADDRESS] (contact: [CLUB E-MAIL]) uses the web tool **Lineup** to prepare the
official lineup sheets for matches. Lineup is operated by [OPERATOR NAME] as our processor.

- **Data:** your name, your federation (NSSZ) registration number and your cap number; for staff, the
  name and role (coach, doctor, assistant coach, team leader, ball thrower) as written on the sheet. We
  do not put dates of birth, photos, contact details or health information into Lineup. The
  "doctor" is only a name on the sheet.
- **Where it comes from:** from our own club records, entered by our staff.
- **Why and on what basis:** to register players and prepare the lineup sheet for matches we play (our
  legitimate interest, Art. 6(1)(f) GDPR) [or: to meet the federation's registration rules, Art.
  6(1)(c); the club decides after checking the rules].
- **Who sees it:** the members of our team in Lineup; the match officials and the federation, to whom
  the printed sheet is handed or sent as usual; and Lineup's providers (Supabase in Ireland, Fly.io
  in Amsterdam, Cloudflare) as processors.
- **How long:** until the player or staff member leaves the club, then we delete the entry from
  Lineup; saved lineups are deleted when we no longer need them. Backups, if any, can keep deleted
  data for up to 30 days.
- **Your rights:** access, correction, erasure, restriction and objection (GDPR Arts. 15–21). For a
  child under 18 the parent can act. Write to [CLUB E-MAIL]. You can complain to NAIH
  (www.naih.hu, 1055 Budapest, Falk Miksa utca 9-11.) or go to court.
- **Lineup's own notice** (for people who sign in) is at [APP URL].

---

## 4. Minta sportszervezeteknek, magyarul (14. cikk)

*Az egyesület szabja testre, és adja át a játékosoknak, a stábtagoknak, kiskorúak esetén a
szülőknek. Az adatkezelő az egyesület; a Lineup az adatfeldolgozója. A játékosok nem jelentkeznek be a
Lineupba, és nem ők adják meg az adataikat, ezért ez a 14. cikk szerinti tájékoztatás, amelyet egy
hónapon belül, legkésőbb az első kapcsolatfelvételkor át kell adni.*

**Adatkezelési tájékoztató a(z) [EGYESÜLET NEVE] játékosainak, stábtagjainak és szüleinek**

A(z) [EGYESÜLET NEVE], [EGYESÜLET CÍME] (kapcsolat: [EGYESÜLET E-MAIL-CÍME]) a **Lineup** webes
eszközt használja a mérkőzések hivatalos rajtlistájának elkészítéséhez. A Lineupot a(z) [OPERATOR
NAME] üzemelteti, a mi adatfeldolgozónkként.

- **Adatok:** a neved, a szövetségi (NSSZ) nyilvántartási számod és a sapkaszámod; a stábtagoknál a
  lapon szereplő név és beosztás (edző, orvos, másodedző, csapatvezető, labdaadogató). Születési időt,
  fényképet, elérhetőséget vagy egészségügyi adatot nem viszünk be a Lineupba. Az "orvos" csak egy
  név a lapon.
- **Honnan származik:** az egyesületi nyilvántartásunkból, a munkatársaink viszik be.
- **Miért és milyen jogalapon:** a játékosok nyilvántartásba vétele és a rajtlista elkészítése a
  mérkőzéseinkhez (jogos érdekünk, GDPR 6. cikk (1) f)) [vagy: a szövetség nyilvántartási szabályainak
  teljesítése, 6. cikk (1) c); ezt az egyesület dönti el a szabályok ellenőrzése után].
- **Ki látja:** a csapatunk tagjai a Lineupban; a játékvezetők és a szövetség, akiknek a kinyomtatott
  vagy elküldött lapot a szokásos módon átadjuk; valamint a Lineup szolgáltatói (Supabase, Írország;
  Fly.io, Amszterdam; Cloudflare) adatfeldolgozóként.
- **Meddig:** amíg a játékos vagy stábtag az egyesület tagja, utána töröljük a bejegyzést a Lineupból;
  a mentett összeállításokat töröljük, ha már nincs rájuk szükség. A biztonsági mentések, ha vannak,
  a törölt adatot legfeljebb 30 napig őrizhetik.
- **Jogaid:** hozzáférés, helyesbítés, törlés, korlátozás és tiltakozás (GDPR 15–21. cikk). Kiskorú
  esetén a szülő is eljárhat. Írj a(z) [EGYESÜLET E-MAIL-CÍME] címre. Panasszal fordulhatsz a NAIH-hoz
  (www.naih.hu, 1055 Budapest, Falk Miksa utca 9-11.), vagy bírósághoz.
- **A Lineup saját tájékoztatója** (a bejelentkezőknek) itt érhető el: [APP URL].
