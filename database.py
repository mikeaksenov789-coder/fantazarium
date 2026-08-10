import sqlite3
import hashlib
import secrets
import random
import os


BAZA = "fantazarium.db"
PAPKA_KART = "static/cards"
KART_V_RUKE = 6
ALFAVIT = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Сколько очков нужно для победы. Поменяй это число, если хочешь партию короче.
OCHKOV_DLYA_POBEDY = 30


# ========== ТАБЛИЦЫ ==========

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
            status TEXT NOT NULL
        )
    """)
    kursor.execute("""
        CREATE TABLE IF NOT EXISTS uchastniki (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod_komnaty TEXT NOT NULL,
            login TEXT NOT NULL,
            ochki INTEGER NOT NULL
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


# ========== ПОЛЬЗОВАТЕЛИ ==========

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


# ========== КОМНАТЫ ==========

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
        "INSERT INTO komnaty (kod, hozyain, status) VALUES (?, ?, ?)",
        (kod, login, "ozhidanie")
    )
    kursor.execute(
        "INSERT INTO uchastniki (kod_komnaty, login, ochki) VALUES (?, ?, ?)",
        (kod, login, 0)
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

    # В идущую игру входить нельзя
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
            "INSERT INTO uchastniki (kod_komnaty, login, ochki) VALUES (?, ?, ?)",
            (kod, login, 0)
        )
        soedinenie.commit()
    soedinenie.close()
    return True


def poluchit_igrokov(kod):
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute(
        "SELECT login, ochki FROM uchastniki WHERE kod_komnaty = ? ORDER BY id",
        (kod,)
    )
    stroki = kursor.fetchall()
    soedinenie.close()
    return [{"login": s[0], "ochki": s[1]} for s in stroki]


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
    """Убирает игрока из комнаты вместе с его картами."""
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
    """Обнуляет счёт и очищает всё для новой игры."""
    soedinenie = sqlite3.connect(BAZA)
    kursor = soedinenie.cursor()
    kursor.execute("UPDATE uchastniki SET ochki = 0 WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM ruki WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM raundy WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM hody WHERE kod_komnaty = ?", (kod,))
    kursor.execute("DELETE FROM golosa WHERE kod_komnaty = ?", (kod,))
    soedinenie.commit()
    soedinenie.close()


# ========== КАРТЫ ==========

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


# ========== РАУНДЫ ==========

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


# ========== ГОЛОСОВАНИЕ ==========

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


# ========== ПОДСЧЁТ ОЧКОВ ==========

def poschitat_ochki(kod, nomer):
    """
    Правила Фантазариума:
    - Угадали все или никто -> все кроме ведущего +2
    - Угадала часть -> ведущему +2 и ещё по 1 за каждого угадавшего,
                       угадавшим +3
    - Бонус: +1 за каждый чужой голос за свою карту
    """
    raund = tekushiy_raund(kod)
    vedushiy = raund["vedushiy"]
    karta_vedushego = raund["karta_vedushego"]

    hody = poluchit_hody(kod, nomer)
    golosa = poluchit_golosa(kod, nomer)
    igroki = poluchit_igrokov(kod)

    avtor_karty = {h["karta"]: h["login"] for h in hody}
    ugadali = [g["login"] for g in golosa if g["karta"] == karta_vedushego]

    vsego_golosuyushih = len(igroki) - 1
    itog = {i["login"]: 0 for i in igroki}

    if len(ugadali) == vsego_golosuyushih or len(ugadali) == 0:
        for igrok in igroki:
            if igrok["login"] != vedushiy:
                itog[igrok["login"]] += 2
    else:
        itog[vedushiy] += 2 + len(ugadali)
        for login in ugadali:
            itog[login] += 3

    for golos in golosa:
        avtor = avtor_karty.get(golos["karta"])
        if avtor is not None and avtor != vedushiy:
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


# ========== КОНЕЦ ПАРТИИ ==========

def est_pobeditel(kod):
    """Проверяет, набрал ли кто-то нужное количество очков."""
    for igrok in poluchit_igrokov(kod):
        if igrok["ochki"] >= OCHKOV_DLYA_POBEDY:
            return True
    return False


def hvatit_kart(kod):
    """Хватит ли карт на ещё один раунд."""
    igroki = poluchit_igrokov(kod)
    nuzhno = 0
    for igrok in igroki:
        nuzhno += KART_V_RUKE - len(poluchit_ruku(kod, igrok["login"]))
    return skolko_svobodnyh_kart(kod) >= nuzhno


def tablica_pobediteley(kod):
    """Игроки, отсортированные по очкам."""
    igroki = poluchit_igrokov(kod)
    igroki.sort(key=lambda i: i["ochki"], reverse=True)

    mesto = 1
    for i, igrok in enumerate(igroki):
        if i > 0 and igrok["ochki"] < igroki[i - 1]["ochki"]:
            mesto = i + 1
        igrok["mesto"] = mesto

    return igroki