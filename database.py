import sqlite3
import hashlib
import secrets
import random
import os
import time
import shutil


BAZA = "fantazarium.db"
KART_V_RUKE = 6
ALFAVIT = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

OCHKOV_DLYA_POBEDY = 30
SEKUND_NA_HOD = 120
CENA_ZAMENY = 5
MAKS_IGROKOV = 7

KOLODY = {
    "omut": {
        "nazvanie": "Тихий омут",
        "papka": "omut",
        "opisanie": "Сны, память, страхи. Глубже и сложнее"
    },
    "balagan": {
        "nazvanie": "Шумный балаган",
        "papka": "balagan",
        "opisanie": "Города, звери, море. Проще и веселее"
    }
}


def sozdat_tablicu():
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS igroki (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            hash_parolya TEXT NOT NULL,
            sol TEXT NOT NULL
        )
    """)
    soedinenie.commit()
    soedinenie.close()


def sozdat_tablicy_komnat():
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS komnaty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT UNIQUE NOT NULL,
            hozyain TEXT NOT NULL,
            status TEXT NOT NULL,
            deadline REAL,
            koloda TEXT NOT NULL DEFAULT 'omut',
            publichnaya INTEGER NOT NULL DEFAULT 0,
            sozdana REAL NOT NULL DEFAULT 0
        )
    """)
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS uchastniki (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod_komnaty TEXT NOT NULL,
            login TEXT NOT NULL,
            ochki INTEGER NOT NULL,
            gotov INTEGER NOT NULL DEFAULT 0
        )
    """)
    soedinenie.commit()
    soedinenie.close()


def sozdat_tablicu_kart():
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS ruki (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod_komnaty TEXT NOT NULL,
            login TEXT NOT NULL,
            karta TEXT NOT NULL
        )
    """)
    soedinenie.commit()
    soedinenie.close()


def sozdat_tablicu_raundov():
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS raundy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod_komnaty TEXT NOT NULL,
            nomer INTEGER NOT NULL,
            vedushiy TEXT NOT NULL,
            associaciya TEXT,
            karta_vedushego TEXT
        )
    """)
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS hody (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod_komnaty TEXT NOT NULL,
            nomer_raunda INTEGER NOT NULL,
            login TEXT NOT NULL,
            karta TEXT NOT NULL
        )
    """)
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS golosa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod_komnaty TEXT NOT NULL,
            nomer_raunda INTEGER NOT NULL,
            login TEXT NOT NULL,
            karta TEXT NOT NULL
        )
    """)
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS sbrosy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod_komnaty TEXT NOT NULL,
            karta TEXT NOT NULL
        )
    """)
    soedinenie.commit()
    soedinenie.close()


def sdelat_hash(parol, sol):
    return hashlib.sha256((parol + sol).encode()).hexdigest()


def dobavit_igroka(login, parol):
    sol = secrets.token_hex(16)
    hash_parolya = sdelat_hash(parol, sol)

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    try:
        kursor.execute(
            "INSERT INTO igroki (login, hash_parolya, sol) VALUES (?, ?, ?)",
            (login, hash_parolya, sol)
        )
        soedinenie.commit()
        rezultat = True
    except sqlite3.IntegrityError:
        rezultat = False
    soedinenie.close()
    return rezultat


def proverit_parol(login, parol):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("SELECT hash_parolya, sol FROM igroki WHERE login = ?", (login,))
    stroka = kursor.fetchone()
    soedinenie.close()

    if stroka is None:
        return False
    return sdelat_hash(parol, stroka[1]) == stroka[0]


def pridumat_kod():
    return "".join(random.choice(ALFAVIT) for _ in range(5))


def sozdat_komnatu(login, koloda="omut", publichnaya=False):
    if koloda not in KOLODY:
        koloda = "omut"

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    while True:
        kod = pridumat_kod()
        kursor.execute("SELECT id FROM komnaty WHERE kod = ?", (kod,))
        if kursor.fetchone() is None:
            break

    kursor.execute(
        "INSERT INTO komnaty (kod, hozyain, status, deadline, koloda, publichnaya, sozdana) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (kod, login, "ozhidanie", None, koloda, 1 if publichnaya else 0, time.time())
    )
    kursor.execute(
        "INSERT INTO uchastniki (kod_komnaty, login, ochki, gotov) VALUES (?, ?, ?, ?)",
        (kod, login, 0, 0)
    )
    soedinenie.commit()
    soedinenie.close()
    return kod


def nayti_publichnuyu(koloda, login):
    """Ищет открытую публичную комнату с этой колодой, где есть место."""
    if koloda not in KOLODY:
        return None

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    kursor.execute(
        "SELECT k.kod FROM komnaty k "
        "WHERE k.publichnaya = 1 AND k.koloda = ? AND k.status = 'ozhidanie' "
        "AND (SELECT COUNT(*) FROM uchastniki u WHERE u.kod_komnaty = k.kod) < ? "
        "AND (SELECT COUNT(*) FROM uchastniki u WHERE u.kod_komnaty = k.kod) > 0 "
        "ORDER BY k.sozdana ASC LIMIT 1",
        (koloda, MAKS_IGROKOV)
    )
    stroka = kursor.fetchone()
    soedinenie.close()

    return stroka[0] if stroka else None


def poluchit_kolodu(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("SELECT koloda FROM komnaty WHERE kod = ?", (kod,))
    stroka = kursor.fetchone()
    soedinenie.close()
    return stroka[0] if stroka else "omut"


def komnata_publichnaya(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("SELECT publichnaya FROM komnaty WHERE kod = ?", (kod,))
    stroka = kursor.fetchone()
    soedinenie.close()
    return stroka[0] == 1 if stroka else False


def skolko_igraet_publichno(koloda):
    """Сколько человек сейчас в публичных комнатах этой колоды."""
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT COUNT(*) FROM uchastniki u "
        "JOIN komnaty k ON k.kod = u.kod_komnaty "
        "WHERE k.publichnaya = 1 AND k.koloda = ? AND k.status = 'ozhidanie'",
        (koloda,)
    )
    stroka = kursor.fetchone()
    soedinenie.close()
    return stroka[0] if stroka else 0


def komnata_sushestvuet(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("SELECT id FROM komnaty WHERE kod = ?", (kod,))
    stroka = kursor.fetchone()
    soedinenie.close()
    return stroka is not None


def dobavit_v_komnatu(kod, login):
    if not komnata_sushestvuet(kod):
        return False

    if poluchit_status(kod) != "ozhidanie":
        soedinenie = sqlite3.connect(BAZA)
        kursor = soedinenie.cursor()
        kursor.execute(
            "SELECT id FROM uchastniki WHERE kod_komnaty = ? AND login = ?",
            (kod, login)
        )
        uzhe_igraet = kursor.fetchone() is not None
        soedinenie.close()
        return uzhe_igraet

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT id FROM uchastniki WHERE kod_komnaty = ? AND login = ?",
        (kod, login)
    )
    if kursor.fetchone() is None:
        kursor.execute("SELECT COUNT(*) FROM uchastniki WHERE kod_komnaty = ?", (kod,))
        if kursor.fetchone()[0] >= MAKS_IGROKOV:
            soedinenie.close()
            return False

        kursor.execute(
            "INSERT INTO uchastniki (kod_komnaty, login, ochki, gotov) VALUES (?, ?, ?, ?)",
            (kod, login, 0, 0)
        )
        soedinenie.commit()
    soedinenie.close()
    return True


def poluchit_igrokov(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT login, ochki, gotov FROM uchastniki WHERE kod_komnaty = ? ORDER BY id",
        (kod,)
    )
    stroki = kursor.fetchall()
    soedinenie.close()
    return [{"login": s[0], "ochki": s[1], "gotov": s[2] == 1} for s in stroki]


def poluchit_ochki_igroka(kod, login):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT ochki FROM uchastniki WHERE kod_komnaty = ? AND login = ?",
        (kod, login)
    )
    stroka = kursor.fetchone()
    soedinenie.close()
    return stroka[0] if stroka else 0


def pomenyat_gotovnost(kod, login):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT gotov FROM uchastniki WHERE kod_komnaty = ? AND login = ?",
        (kod, login)
    )
    stroka = kursor.fetchone()

    if stroka is None:
        soedinenie.close()
        return False

    novoe = 0 if stroka[0] == 1 else 1
    kursor.execute(
        "UPDATE uchastniki SET gotov = ? WHERE kod_komnaty = ? AND login = ?",
        (novoe, kod, login)
    )
    soedinenie.commit()
    soedinenie.close()
    return novoe == 1


def sbrosit_gotovnost(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("UPDATE uchastniki SET gotov = 0 WHERE kod_komnaty = ?", (kod,))
    soedinenie.commit()
    soedinenie.close()


def vse_gotovy(kod):
    igroki = poluchit_igrokov(kod)
    if len(igroki) == 0:
        return False
    for igrok in igroki:
        if not igrok["gotov"]:
            return False
    return True


def skolko_gotovyh(kod):
    return len([i for i in poluchit_igrokov(kod) if i["gotov"]])


def poluchit_hozyaina(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("SELECT hozyain FROM komnaty WHERE kod = ?", (kod,))
    stroka = kursor.fetchone()
    soedinenie.close()
    return stroka[0] if stroka else None


def naznachit_hozyaina(kod, login):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("UPDATE komnaty SET hozyain = ? WHERE kod = ?", (login, kod))
    soedinenie.commit()
    soedinenie.close()


def izmenit_status(kod, noviy_status):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("UPDATE komnaty SET status = ? WHERE kod = ?", (noviy_status, kod))
    soedinenie.commit()
    soedinenie.close()


def poluchit_status(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("SELECT status FROM komnaty WHERE kod = ?", (kod,))
    stroka = kursor.fetchone()
    soedinenie.close()
    return stroka[0] if stroka else None


def zapustit_taymer(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "UPDATE komnaty SET deadline = ? WHERE kod = ?",
        (time.time() + SEKUND_NA_HOD, kod)
    )
    soedinenie.commit()
    soedinenie.close()


def sbrosit_taymer(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("UPDATE komnaty SET deadline = NULL WHERE kod = ?", (kod,))
    soedinenie.commit()
    soedinenie.close()


def poluchit_deadline(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("SELECT deadline FROM komnaty WHERE kod = ?", (kod,))
    stroka = kursor.fetchone()
    soedinenie.close()
    return stroka[0] if stroka else None


def ostalos_sekund(kod):
    deadline = poluchit_deadline(kod)
    if deadline is None:
        return None
    return max(0, int(deadline - time.time()))


def vremya_vyshlo(kod):
    deadline = poluchit_deadline(kod)
    if deadline is None:
        return False
    return time.time() > deadline


def dobavit_ochki(kod, login, skolko):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "UPDATE uchastniki SET ochki = ochki + ? WHERE kod_komnaty = ? AND login = ?",
        (skolko, kod, login)
    )
    soedinenie.commit()
    soedinenie.close()


def vygnat_igroka(kod, login):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "DELETE FROM uchastniki WHERE kod_komnaty = ? AND login = ?",
        (kod, login)
    )
    kursor.execute(
        "DELETE FROM ruki WHERE kod_komnaty = ? AND login = ?",
        (kod, login)
    )
    soedinenie.commit()
    soedinenie.close()

    # Если ушёл хозяин, назначаем первого оставшегося
    if poluchit_hozyaina(kod) == login:
        ostalis = poluchit_igrokov(kod)
        if len(ostalis) > 0:
            naznachit_hozyaina(kod, ostalis[0]["login"])


def novaya_partiya(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("UPDATE uchastniki SET ochki = 0, gotov = 0 WHERE kod_komnaty = ?", (kod,))
    kursor.execute("UPDATE komnaty SET deadline = NULL WHERE kod = ?", (kod,))
    kursor.execute("DELETE FROM ruki WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM raundy WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM hody WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM golosa WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM sbrosy WHERE kod_komnaty = ?", (kod,))
    soedinenie.commit()
    soedinenie.close()


def spisok_vseh_kart(koloda):
    """Возвращает пути вида omut/card_001.jpg"""
    if koloda not in KOLODY:
        koloda = "omut"

    papka = KOLODY[koloda]["papka"]
    polnyy_put = os.path.join("static", "cards", papka)

    if not os.path.isdir(polnyy_put):
        return []

    faily = os.listdir(polnyy_put)
    kartinki = [f for f in faily if f.endswith((".png", ".jpg", ".jpeg"))]
    kartinki.sort()
    return [papka + "/" + f for f in kartinki]


def skolko_kart_v_kolode(koloda):
    return len(spisok_vseh_kart(koloda))


def zanyatye_karty(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    kursor.execute("SELECT karta FROM ruki WHERE kod_komnaty = ?", (kod,))
    v_rukah = [s[0] for s in kursor.fetchall()]

    kursor.execute("SELECT karta FROM hody WHERE kod_komnaty = ?", (kod,))
    sygrannye = [s[0] for s in kursor.fetchall()]

    kursor.execute("SELECT karta FROM sbrosy WHERE kod_komnaty = ?", (kod,))
    sbroshennye = [s[0] for s in kursor.fetchall()]

    soedinenie.close()
    return set(v_rukah + sygrannye + sbroshennye)


def svobodnye_karty(kod):
    koloda = poluchit_kolodu(kod)
    zanyaty = zanyatye_karty(kod)
    return [k for k in spisok_vseh_kart(koloda) if k not in zanyaty]


def skolko_svobodnyh_kart(kod):
    return len(svobodnye_karty(kod))


def razdat_karty(kod):
    igroki = poluchit_igrokov(kod)
    koloda = spisok_vseh_kart(poluchit_kolodu(kod))

    if len(koloda) < len(igroki) * KART_V_RUKE:
        return False

    random.shuffle(koloda)

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("DELETE FROM ruki WHERE kod_komnaty = ?", (kod,))

    nomer = 0
    for igrok in igroki:
        for _ in range(KART_V_RUKE):
            kursor.execute(
                "INSERT INTO ruki (kod_komnaty, login, karta) VALUES (?, ?, ?)",
                (kod, igrok["login"], koloda[nomer])
            )
            nomer = nomer + 1

    soedinenie.commit()
    soedinenie.close()
    return True


def dobrat_karty(kod):
    igroki = poluchit_igrokov(kod)
    svobodnye = svobodnye_karty(kod)
    random.shuffle(svobodnye)

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    nomer = 0
    for igrok in igroki:
        kursor.execute(
            "SELECT COUNT(*) FROM ruki WHERE kod_komnaty = ? AND login = ?",
            (kod, igrok["login"])
        )
        est = kursor.fetchone()[0]

        for _ in range(KART_V_RUKE - est):
            if nomer >= len(svobodnye):
                break
            kursor.execute(
                "INSERT INTO ruki (kod_komnaty, login, karta) VALUES (?, ?, ?)",
                (kod, igrok["login"], svobodnye[nomer])
            )
            nomer = nomer + 1

    soedinenie.commit()
    soedinenie.close()


def poluchit_ruku(kod, login):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT karta FROM ruki WHERE kod_komnaty = ? AND login = ? ORDER BY id",
        (kod, login)
    )
    stroki = kursor.fetchall()
    soedinenie.close()
    return [s[0] for s in stroki]


def mozhno_zamenit(kod, login):
    if poluchit_ochki_igroka(kod, login) < CENA_ZAMENY:
        return False

    skolko_v_ruke = len(poluchit_ruku(kod, login))
    if skolko_v_ruke == 0:
        return False

    return skolko_svobodnyh_kart(kod) >= skolko_v_ruke


def zamenit_ruku(kod, login):
    if not mozhno_zamenit(kod, login):
        return False

    staraya_ruka = poluchit_ruku(kod, login)
    svobodnye = svobodnye_karty(kod)
    random.shuffle(svobodnye)

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    for karta in staraya_ruka:
        kursor.execute(
            "INSERT INTO sbrosy (kod_komnaty, karta) VALUES (?, ?)",
            (kod, karta)
        )

    kursor.execute(
        "DELETE FROM ruki WHERE kod_komnaty = ? AND login = ?",
        (kod, login)
    )

    for i in range(len(staraya_ruka)):
        kursor.execute(
            "INSERT INTO ruki (kod_komnaty, login, karta) VALUES (?, ?, ?)",
            (kod, login, svobodnye[i])
        )

    kursor.execute(
        "UPDATE uchastniki SET ochki = ochki - ? WHERE kod_komnaty = ? AND login = ?",
        (CENA_ZAMENY, kod, login)
    )

    soedinenie.commit()
    soedinenie.close()
    return True


def ubrat_kartu_iz_ruki(kod, login, karta):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "DELETE FROM ruki WHERE kod_komnaty = ? AND login = ? AND karta = ?",
        (kod, login, karta)
    )
    soedinenie.commit()
    soedinenie.close()


def nachat_raund(kod, nomer):
    igroki = poluchit_igrokov(kod)
    vedushiy = igroki[(nomer - 1) % len(igroki)]["login"]

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "INSERT INTO raundy (kod_komnaty, nomer, vedushiy) VALUES (?, ?, ?)",
        (kod, nomer, vedushiy)
    )
    soedinenie.commit()
    soedinenie.close()
    return vedushiy


def tekushiy_raund(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT nomer, vedushiy, associaciya, karta_vedushego "
        "FROM raundy WHERE kod_komnaty = ? ORDER BY nomer DESC LIMIT 1",
        (kod,)
    )
    stroka = kursor.fetchone()
    soedinenie.close()

    if stroka is None:
        return None
    return {
        "nomer": stroka[0],
        "vedushiy": stroka[1],
        "associaciya": stroka[2],
        "karta_vedushego": stroka[3]
    }


def sohranit_associaciyu(kod, nomer, associaciya, karta):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "UPDATE raundy SET associaciya = ?, karta_vedushego = ? "
        "WHERE kod_komnaty = ? AND nomer = ?",
        (associaciya, karta, kod, nomer)
    )
    soedinenie.commit()
    soedinenie.close()


def sohranit_hod(kod, nomer, login, karta):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT id FROM hody WHERE kod_komnaty = ? AND nomer_raunda = ? AND login = ?",
        (kod, nomer, login)
    )
    if kursor.fetchone() is None:
        kursor.execute(
            "INSERT INTO hody (kod_komnaty, nomer_raunda, login, karta) VALUES (?, ?, ?, ?)",
            (kod, nomer, login, karta)
        )
        soedinenie.commit()
    soedinenie.close()


def poluchit_hody(kod, nomer):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT login, karta FROM hody WHERE kod_komnaty = ? AND nomer_raunda = ? ORDER BY karta",
        (kod, nomer)
    )
    stroki = kursor.fetchall()
    soedinenie.close()
    return [{"login": s[0], "karta": s[1]} for s in stroki]


def kto_mozhet_golosovat(kod, nomer):
    raund = tekushiy_raund(kod)
    if raund is None:
        return []

    hody = poluchit_hody(kod, nomer)
    igroki = [i["login"] for i in poluchit_igrokov(kod)]

    return [
        h["login"] for h in hody
        if h["login"] != raund["vedushiy"] and h["login"] in igroki
    ]


def sohranit_golos(kod, nomer, login, karta):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT id FROM golosa WHERE kod_komnaty = ? AND nomer_raunda = ? AND login = ?",
        (kod, nomer, login)
    )
    if kursor.fetchone() is None:
        kursor.execute(
            "INSERT INTO golosa (kod_komnaty, nomer_raunda, login, karta) VALUES (?, ?, ?, ?)",
            (kod, nomer, login, karta)
        )
        soedinenie.commit()
    soedinenie.close()


def poluchit_golosa(kod, nomer):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT login, karta FROM golosa WHERE kod_komnaty = ? AND nomer_raunda = ?",
        (kod, nomer)
    )
    stroki = kursor.fetchall()
    soedinenie.close()
    return [{"login": s[0], "karta": s[1]} for s in stroki]


def poschitat_ochki(kod, nomer):
    raund = tekushiy_raund(kod)
    vedushiy = raund["vedushiy"]
    karta_vedushego = raund["karta_vedushego"]

    hody = poluchit_hody(kod, nomer)
    golosa = poluchit_golosa(kod, nomer)
    igroki = poluchit_igrokov(kod)

    itog = {i["login"]: 0 for i in igroki}

    if len(hody) <= 1:
        return itog

    if len(hody) == 2:
        for hod in hody:
            if hod["login"] in itog:
                itog[hod["login"]] += 2
        for login, ochki in itog.items():
            if ochki > 0:
                dobavit_ochki(kod, login, ochki)
        return itog

    avtor_karty = {h["karta"]: h["login"] for h in hody}
    ugadali = [g["login"] for g in golosa if g["karta"] == karta_vedushego]
    vsego_golosovalo = len(golosa)

    if vsego_golosovalo == 0:
        return itog

    if len(ugadali) == vsego_golosovalo or len(ugadali) == 0:
        for golos in golosa:
            if golos["login"] in itog:
                itog[golos["login"]] += 2
    else:
        if vedushiy in itog:
            itog[vedushiy] += 2 + len(ugadali)
        for login in ugadali:
            if login in itog:
                itog[login] += 3

    for golos in golosa:
        avtor = avtor_karty.get(golos["karta"])
        if avtor is not None and avtor != vedushiy and avtor in itog:
            itog[avtor] += 1

    for login, ochki in itog.items():
        if ochki > 0:
            dobavit_ochki(kod, login, ochki)

    return itog


def itogi_raunda(kod, nomer):
    raund = tekushiy_raund(kod)
    hody = poluchit_hody(kod, nomer)
    golosa = poluchit_golosa(kod, nomer)

    rezultat = []
    for hod in hody:
        kto_golosoval = [g["login"] for g in golosa if g["karta"] == hod["karta"]]
        rezultat.append({
            "karta": hod["karta"],
            "avtor": hod["login"],
            "golosovali": kto_golosoval,
            "eto_vedushego": hod["karta"] == raund["karta_vedushego"]
        })

    return rezultat


def est_pobeditel(kod):
    for igrok in poluchit_igrokov(kod):
        if igrok["ochki"] >= OCHKOV_DLYA_POBEDY:
            return True
    return False


def hvatit_kart(kod):
    igroki = poluchit_igrokov(kod)
    nuzhno = 0
    for igrok in igroki:
        nuzhno += KART_V_RUKE - len(poluchit_ruku(kod, igrok["login"]))
    return skolko_svobodnyh_kart(kod) >= nuzhno


def tablica_pobediteley(kod):
    igroki = poluchit_igrokov(kod)
    igroki.sort(key=lambda i: i["ochki"], reverse=True)

    mesto = 1
    for i, igrok in enumerate(igroki):
        if i > 0 and igrok["ochki"] < igroki[i - 1]["ochki"]:
            mesto = i + 1
        igrok["mesto"] = mesto

    return igroki

PAPKA_AVATAROV = os.path.join("static", "avatars")
YAZYKI = ["ru", "en", "es", "de", "fr", "zh"]


def sozdat_tablicu_profilya():
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    kursor.execute("""
        CREATE TABLE IF NOT EXISTS profili (
            login TEXT PRIMARY KEY,
            yazyk TEXT NOT NULL DEFAULT 'ru',
            avatar TEXT,
            igr INTEGER NOT NULL DEFAULT 0,
            pobed INTEGER NOT NULL DEFAULT 0,
            ochkov_vsego INTEGER NOT NULL DEFAULT 0
        )
    """)

    kursor.execute("""
        CREATE TABLE IF NOT EXISTS zapisannye (
            kod TEXT PRIMARY KEY
        )
    """)

    soedinenie.commit()
    soedinenie.close()


def sozdat_profil(login, yazyk="ru"):
    if yazyk not in YAZYKI:
        yazyk = "ru"

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "INSERT OR IGNORE INTO profili (login, yazyk) VALUES (?, ?)",
        (login, yazyk)
    )
    soedinenie.commit()
    soedinenie.close()


def poluchit_profil(login):
    sozdat_profil(login)

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT yazyk, avatar, igr, pobed, ochkov_vsego FROM profili WHERE login = ?",
        (login,)
    )
    stroka = kursor.fetchone()
    soedinenie.close()

    if stroka is None:
        return {"yazyk": "ru", "avatar": None, "igr": 0, "pobed": 0, "ochkov_vsego": 0}

    return {
        "yazyk": stroka[0],
        "avatar": stroka[1],
        "igr": stroka[2],
        "pobed": stroka[3],
        "ochkov_vsego": stroka[4]
    }


def ustanovit_yazyk(login, yazyk):
    if yazyk not in YAZYKI:
        return
    sozdat_profil(login)

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("UPDATE profili SET yazyk = ? WHERE login = ?", (yazyk, login))
    soedinenie.commit()
    soedinenie.close()


def ustanovit_avatar(login, imya_fayla):
    sozdat_profil(login)

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("UPDATE profili SET avatar = ? WHERE login = ?", (imya_fayla, login))
    soedinenie.commit()
    soedinenie.close()


def avatary_igrokov(kod):
    """Возвращает словарь логин -> имя файла аватара."""
    igroki = poluchit_igrokov(kod)
    itog = {}

    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    for igrok in igroki:
        kursor.execute("SELECT avatar FROM profili WHERE login = ?", (igrok["login"],))
        stroka = kursor.fetchone()
        if stroka and stroka[0]:
            itog[igrok["login"]] = stroka[0]

    soedinenie.close()
    return itog


def zapisat_rezultaty(kod):
    """Записывает статистику партии. Только один раз на комнату."""
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    kursor.execute("SELECT kod FROM zapisannye WHERE kod = ?", (kod,))
    if kursor.fetchone() is not None:
        soedinenie.close()
        return

    kursor.execute("INSERT INTO zapisannye (kod) VALUES (?)", (kod,))
    soedinenie.commit()
    soedinenie.close()

    tablica = tablica_pobediteley(kod)

    for igrok in tablica:
        sozdat_profil(igrok["login"])

        soedinenie = sqlite3.connect(BAZA)
        kursor = soedinenie.cursor()

        pobeda = 1 if igrok["mesto"] == 1 else 0
        kursor.execute(
            "UPDATE profili SET igr = igr + 1, pobed = pobed + ?, "
            "ochkov_vsego = ochkov_vsego + ? WHERE login = ?",
            (pobeda, igrok["ochki"], igrok["login"])
        )

        soedinenie.commit()
        soedinenie.close()


def ochistit_zapis(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("DELETE FROM zapisannye WHERE kod = ?", (kod,))
    soedinenie.commit()
    soedinenie.close()

def sozdat_tablicu_perevodov():
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS perevody (
            fraza TEXT NOT NULL,
            yazyk TEXT NOT NULL,
            perevod TEXT NOT NULL,
            PRIMARY KEY (fraza, yazyk)
        )
    """)
    soedinenie.commit()
    soedinenie.close()


def vzyat_perevod(fraza, yazyk):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT perevod FROM perevody WHERE fraza = ? AND yazyk = ?",
        (fraza, yazyk)
    )
    stroka = kursor.fetchone()
    soedinenie.close()
    return stroka[0] if stroka else None


def sohranit_perevod(fraza, yazyk, perevod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "INSERT OR REPLACE INTO perevody (fraza, yazyk, perevod) VALUES (?, ?, ?)",
        (fraza, yazyk, perevod)
    )
    soedinenie.commit()
    soedinenie.close()