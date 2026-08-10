import sqlite3
import hashlib
import secrets
import random
import os
import time


BAZA = "fantazarium.db"
PAPKA_KART = "static/cards"
KART_V_RUKE = 6
ALFAVIT = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

OCHKOV_DLYA_POBEDY = 30
SEKUND_NA_HOD = 45


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
            deadline REAL
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


def sozdat_komnatu(login):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    while True:
        kod = pridumat_kod()
        kursor.execute("SELECT id FROM komnaty WHERE kod = ?", (kod,))
        if kursor.fetchone() is None:
            break

    kursor.execute(
        "INSERT INTO komnaty (kod, hozyain, status, deadline) VALUES (?, ?, ?, ?)",
        (kod, login, "ozhidanie", None)
    )
    kursor.execute(
        "INSERT INTO uchastniki (kod_komnaty, login, ochki, gotov) VALUES (?, ?, ?, ?)",
        (kod, login, 0, 0)
    )
    soedinenie.commit()
    soedinenie.close()
    return kod


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


def pomenyat_gotovnost(kod, login):
    """Переключает готовность игрока. Возвращает новое состояние."""
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
    ostatok = deadline - time.time()
    return max(0, int(ostatok))


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


def novaya_partiya(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("UPDATE uchastniki SET ochki = 0, gotov = 0 WHERE kod_komnaty = ?", (kod,))
    kursor.execute("UPDATE komnaty SET deadline = NULL WHERE kod = ?", (kod,))
    kursor.execute("DELETE FROM ruki WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM raundy WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM hody WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM golosa WHERE kod_komnaty = ?", (kod,))
    soedinenie.commit()
    soedinenie.close()


def spisok_vseh_kart():
    faily = os.listdir(PAPKA_KART)
    kartinki = [f for f in faily if f.endswith((".png", ".jpg", ".jpeg"))]
    kartinki.sort()
    return kartinki


def zanyatye_karty(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()

    kursor.execute("SELECT karta FROM ruki WHERE kod_komnaty = ?", (kod,))
    v_rukah = [s[0] for s in kursor.fetchall()]

    kursor.execute("SELECT karta FROM hody WHERE kod_komnaty = ?", (kod,))
    sygrannye = [s[0] for s in kursor.fetchall()]

    soedinenie.close()
    return set(v_rukah + sygrannye)


def skolko_svobodnyh_kart(kod):
    return len([k for k in spisok_vseh_kart() if k not in zanyatye_karty(kod)])


def razdat_karty(kod):
    igroki = poluchit_igrokov(kod)
    koloda = spisok_vseh_kart()

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
    svobodnye = [k for k in spisok_vseh_kart() if k not in zanyatye_karty(kod)]
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
    """
    Очки получают только те, кто реально проголосовал.
    Пропустившие ход остаются без очков.
    """
    raund = tekushiy_raund(kod)
    vedushiy = raund["vedushiy"]
    karta_vedushego = raund["karta_vedushego"]

    hody = poluchit_hody(kod, nomer)
    golosa = poluchit_golosa(kod, nomer)
    igroki = poluchit_igrokov(kod)

    avtor_karty = {h["karta"]: h["login"] for h in hody}
    ugadali = [g["login"] for g in golosa if g["karta"] == karta_vedushego]

    itog = {i["login"]: 0 for i in igroki}
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