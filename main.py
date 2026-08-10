from fastapi import FastAPI, Form, Cookie
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import database

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

database.sozdat_tablicu()
database.sozdat_tablicy_komnat()
database.sozdat_tablicu_kart()
database.sozdat_tablicu_raundov()


def zakonchit_raund(kod):
    raund = database.tekushiy_raund(kod)
    database.poschitat_ochki(kod, raund["nomer"])
    database.sbrosit_taymer(kod)
    database.sbrosit_gotovnost(kod)

    if database.est_pobeditel(kod) or not database.hvatit_kart(kod):
        database.izmenit_status(kod, "konec")
    else:
        database.izmenit_status(kod, "itogi")


def zapustit_sleduyushiy_raund(kod):
    raund = database.tekushiy_raund(kod)
    database.dobrat_karty(kod)
    database.nachat_raund(kod, raund["nomer"] + 1)
    database.sbrosit_gotovnost(kod)
    database.sbrosit_taymer(kod)
    database.izmenit_status(kod, "associaciya")


def proverit_vremya(kod):
    status = database.poluchit_status(kod)

    if status not in ("otvety", "golosovanie"):
        return

    if not database.vremya_vyshlo(kod):
        return

    raund = database.tekushiy_raund(kod)
    if raund is None:
        return

    if status == "otvety":
        hody = database.poluchit_hody(kod, raund["nomer"])

        if len(hody) < 2:
            zakonchit_raund(kod)
        else:
            database.izmenit_status(kod, "golosovanie")
            database.zapustit_taymer(kod)

    elif status == "golosovanie":
        zakonchit_raund(kod)


@app.get("/")
def glavnaya():
    return FileResponse("templates/index.html")


@app.get("/vhod")
def stranica_vhoda():
    return FileResponse("templates/vhod.html")


@app.get("/registraciya")
def stranica_registracii():
    return FileResponse("templates/registraciya.html")


@app.get("/pravila")
def stranica_pravil():
    return FileResponse("templates/pravila.html")


@app.get("/oshibka")
def stranica_oshibki():
    return FileResponse("templates/oshibka.html")


@app.get("/lobbi")
def stranica_lobbi():
    return FileResponse("templates/lobbi.html")


@app.get("/komnata/{kod}")
def stranica_komnaty(kod: str):
    return FileResponse("templates/komnata.html")


@app.get("/igra/{kod}")
def stranica_igry(kod: str):
    return FileResponse("templates/igra.html")


@app.post("/registraciya")
def obrabotat_registraciyu(login: str = Form(), parol: str = Form()):
    login = login.strip()

    if len(login) == 0 or len(login) > 20:
        return RedirectResponse("/registraciya?oshibka=zanyat", status_code=303)

    if not database.dobavit_igroka(login, parol):
        return RedirectResponse("/registraciya?oshibka=zanyat", status_code=303)

    otvet = RedirectResponse("/lobbi", status_code=303)
    otvet.set_cookie(key="login", value=login)
    return otvet


@app.post("/vhod")
def obrabotat_vhod(login: str = Form(), parol: str = Form()):
    login = login.strip()

    if not database.proverit_parol(login, parol):
        return RedirectResponse("/vhod?oshibka=1", status_code=303)

    otvet = RedirectResponse("/lobbi", status_code=303)
    otvet.set_cookie(key="login", value=login)
    return otvet


@app.post("/sozdat_komnatu")
def sozdat_komnatu(login: str = Cookie(default=None)):
    if login is None:
        return RedirectResponse("/vhod", status_code=303)

    kod = database.sozdat_komnatu(login)
    return RedirectResponse("/komnata/" + kod, status_code=303)


@app.post("/voyti_v_komnatu")
def voyti_v_komnatu(kod: str = Form(), login: str = Cookie(default=None)):
    if login is None:
        return RedirectResponse("/vhod", status_code=303)

    kod = kod.strip().upper()

    if not database.komnata_sushestvuet(kod):
        return RedirectResponse("/lobbi?oshibka=net", status_code=303)

    if not database.dobavit_v_komnatu(kod, login):
        return RedirectResponse("/lobbi?oshibka=idet", status_code=303)

    return RedirectResponse("/komnata/" + kod, status_code=303)


@app.post("/gotovnost")
def gotovnost(kod: str = Form(), login: str = Cookie(default=None)):
    """Игрок нажал Готов. Работает и в комнате, и на экране итогов."""
    if login is None:
        return JSONResponse({"oshibka": "Не авторизован"})

    status = database.poluchit_status(kod)

    if status not in ("ozhidanie", "itogi"):
        return JSONResponse({"oshibka": "Сейчас нельзя"})

    database.pomenyat_gotovnost(kod, login)

    if status == "itogi" and database.vse_gotovy(kod):
        zapustit_sleduyushiy_raund(kod)

    return JSONResponse({"ok": True})


@app.post("/nachat_igru")
def nachat_igru(kod: str = Form(), login: str = Cookie(default=None)):
    if login is None:
        return RedirectResponse("/vhod", status_code=303)

    if login != database.poluchit_hozyaina(kod):
        return RedirectResponse("/oshibka", status_code=303)

    if len(database.poluchit_igrokov(kod)) < 4:
        return RedirectResponse("/komnata/" + kod, status_code=303)

    if not database.vse_gotovy(kod):
        return RedirectResponse("/komnata/" + kod, status_code=303)

    database.razdat_karty(kod)
    database.nachat_raund(kod, 1)
    database.sbrosit_gotovnost(kod)
    database.sbrosit_taymer(kod)
    database.izmenit_status(kod, "associaciya")

    return RedirectResponse("/igra/" + kod, status_code=303)


@app.post("/zagadat")
def zagadat(
    kod: str = Form(),
    karta: str = Form(),
    associaciya: str = Form(),
    login: str = Cookie(default=None)
):
    raund = database.tekushiy_raund(kod)

    if raund is None or raund["vedushiy"] != login:
        return JSONResponse({"oshibka": "Ты не ведущий"})

    if database.poluchit_status(kod) != "associaciya":
        return JSONResponse({"oshibka": "Сейчас не время загадывать"})

    associaciya = associaciya.strip()
    if len(associaciya) == 0 or len(associaciya) > 80:
        return JSONResponse({"oshibka": "Ассоциация от 1 до 80 символов"})

    database.sohranit_associaciyu(kod, raund["nomer"], associaciya, karta)
    database.sohranit_hod(kod, raund["nomer"], login, karta)
    database.ubrat_kartu_iz_ruki(kod, login, karta)
    database.izmenit_status(kod, "otvety")
    database.zapustit_taymer(kod)

    return JSONResponse({"ok": True})


@app.post("/sdat_kartu")
def sdat_kartu(kod: str = Form(), karta: str = Form(), login: str = Cookie(default=None)):
    proverit_vremya(kod)

    raund = database.tekushiy_raund(kod)

    if raund is None or raund["vedushiy"] == login:
        return JSONResponse({"oshibka": "Ведущий уже сходил"})

    if database.poluchit_status(kod) != "otvety":
        return JSONResponse({"oshibka": "Время вышло"})

    database.sohranit_hod(kod, raund["nomer"], login, karta)
    database.ubrat_kartu_iz_ruki(kod, login, karta)

    hody = database.poluchit_hody(kod, raund["nomer"])
    igroki = database.poluchit_igrokov(kod)

    if len(hody) >= len(igroki):
        database.izmenit_status(kod, "golosovanie")
        database.zapustit_taymer(kod)

    return JSONResponse({"ok": True})


@app.post("/golosovat")
def golosovat(kod: str = Form(), karta: str = Form(), login: str = Cookie(default=None)):
    proverit_vremya(kod)

    raund = database.tekushiy_raund(kod)

    if raund is None or raund["vedushiy"] == login:
        return JSONResponse({"oshibka": "Ведущий не голосует"})

    if database.poluchit_status(kod) != "golosovanie":
        return JSONResponse({"oshibka": "Время вышло"})

    hody = database.poluchit_hody(kod, raund["nomer"])
    for hod in hody:
        if hod["karta"] == karta and hod["login"] == login:
            return JSONResponse({"oshibka": "Нельзя голосовать за свою карту"})

    database.sohranit_golos(kod, raund["nomer"], login, karta)

    golosa = database.poluchit_golosa(kod, raund["nomer"])
    igroki = database.poluchit_igrokov(kod)

    if len(golosa) >= len(igroki) - 1:
        zakonchit_raund(kod)

    return JSONResponse({"ok": True})


@app.post("/igrat_snova")
def igrat_snova(kod: str = Form(), login: str = Cookie(default=None)):
    if login != database.poluchit_hozyaina(kod):
        return JSONResponse({"oshibka": "Только хозяин может начать заново"})

    database.novaya_partiya(kod)
    database.izmenit_status(kod, "ozhidanie")

    return JSONResponse({"ok": True})


@app.post("/vyyti_iz_igry")
def vyyti_iz_igry(kod: str = Form(), login: str = Cookie(default=None)):
    if login is None:
        return JSONResponse({"oshibka": "Не авторизован"})

    database.vygnat_igroka(kod, login)

    igroki = database.poluchit_igrokov(kod)
    status = database.poluchit_status(kod)

    if len(igroki) < 4 and status not in ("ozhidanie", "konec"):
        database.sbrosit_taymer(kod)
        database.izmenit_status(kod, "konec")
        return JSONResponse({"ok": True})

    raund = database.tekushiy_raund(kod)
    if raund is None:
        return JSONResponse({"ok": True})

    if status == "otvety":
        hody = database.poluchit_hody(kod, raund["nomer"])
        if len(hody) >= len(igroki):
            database.izmenit_status(kod, "golosovanie")
            database.zapustit_taymer(kod)

    elif status == "golosovanie":
        golosa = database.poluchit_golosa(kod, raund["nomer"])
        if len(golosa) >= len(igroki) - 1:
            zakonchit_raund(kod)

    elif status == "itogi":
        if database.vse_gotovy(kod):
            zapustit_sleduyushiy_raund(kod)

    return JSONResponse({"ok": True})


@app.post("/propustit_igroka")
def propustit_igroka(kod: str = Form(), kogo: str = Form(), login: str = Cookie(default=None)):
    if login != database.poluchit_hozyaina(kod):
        return JSONResponse({"oshibka": "Только хозяин может исключать"})

    if kogo == login:
        return JSONResponse({"oshibka": "Нельзя исключить себя"})

    database.vygnat_igroka(kod, kogo)

    igroki = database.poluchit_igrokov(kod)
    status = database.poluchit_status(kod)
    raund = database.tekushiy_raund(kod)

    if len(igroki) < 4 and status not in ("ozhidanie", "konec"):
        database.sbrosit_taymer(kod)
        database.izmenit_status(kod, "konec")
        return JSONResponse({"ok": True})

    if raund is None:
        return JSONResponse({"ok": True})

    if raund["vedushiy"] == kogo and status in ("associaciya", "otvety"):
        database.sbrosit_taymer(kod)
        database.izmenit_status(kod, "associaciya")
        return JSONResponse({"ok": True})

    if status == "otvety":
        hody = database.poluchit_hody(kod, raund["nomer"])
        if len(hody) >= len(igroki):
            database.izmenit_status(kod, "golosovanie")
            database.zapustit_taymer(kod)

    elif status == "golosovanie":
        golosa = database.poluchit_golosa(kod, raund["nomer"])
        if len(golosa) >= len(igroki) - 1:
            zakonchit_raund(kod)

    elif status == "itogi":
        if database.vse_gotovy(kod):
            zapustit_sleduyushiy_raund(kod)

    return JSONResponse({"ok": True})


@app.get("/api/komnata/{kod}")
def dannye_komnaty(kod: str, login: str = Cookie(default=None)):
    if not database.komnata_sushestvuet(kod):
        return JSONResponse({"oshibka": "Комната не найдена"})

    igroki = database.poluchit_igrokov(kod)
    ya_gotov = False
    for igrok in igroki:
        if igrok["login"] == login:
            ya_gotov = igrok["gotov"]

    return JSONResponse({
        "kod": kod,
        "igroki": igroki,
        "hozyain": database.poluchit_hozyaina(kod),
        "status": database.poluchit_status(kod),
        "ya": login,
        "ya_gotov": ya_gotov,
        "gotovyh": database.skolko_gotovyh(kod),
        "vse_gotovy": database.vse_gotovy(kod)
    })


@app.get("/api/igra/{kod}")
def dannye_igry(kod: str, login: str = Cookie(default=None)):
    if not database.komnata_sushestvuet(kod):
        return JSONResponse({"oshibka": "Комната не найдена"})

    proverit_vremya(kod)

    raund = database.tekushiy_raund(kod)
    status = database.poluchit_status(kod)
    igroki = database.poluchit_igrokov(kod)

    ya_gotov = False
    for igrok in igroki:
        if igrok["login"] == login:
            ya_gotov = igrok["gotov"]

    otvet = {
        "kod": kod,
        "status": status,
        "igroki": igroki,
        "moi_karty": database.poluchit_ruku(kod, login),
        "ya": login,
        "hozyain": database.poluchit_hozyaina(kod),
        "porog": database.OCHKOV_DLYA_POBEDY,
        "ostalos": database.ostalos_sekund(kod),
        "ya_gotov": ya_gotov,
        "gotovyh": database.skolko_gotovyh(kod),
        "nomer_raunda": raund["nomer"] if raund else 0,
        "vedushiy": raund["vedushiy"] if raund else None,
        "ya_vedushiy": raund["vedushiy"] == login if raund else False,
        "associaciya": raund["associaciya"] if raund else None
    }

    if status == "konec":
        otvet["tablica"] = database.tablica_pobediteley(kod)
        otvet["sdali"] = 0
        otvet["ya_sdal"] = False
        otvet["karty_na_stole"] = []
        otvet["ya_golosoval"] = False
        otvet["progolosovali"] = 0
        otvet["itogi"] = []
        otvet["zhdem"] = []
        otvet["ostalos"] = None
        return JSONResponse(otvet)

    otvet["tablica"] = []

    if raund is None:
        otvet["sdali"] = 0
        otvet["ya_sdal"] = False
        otvet["karty_na_stole"] = []
        otvet["ya_golosoval"] = False
        otvet["progolosovali"] = 0
        otvet["itogi"] = []
        otvet["zhdem"] = []
        return JSONResponse(otvet)

    hody = database.poluchit_hody(kod, raund["nomer"])
    golosa = database.poluchit_golosa(kod, raund["nomer"])

    otvet["sdali"] = len(hody)
    otvet["ya_sdal"] = any(h["login"] == login for h in hody)
    otvet["progolosovali"] = len(golosa)
    otvet["ya_golosoval"] = any(g["login"] == login for g in golosa)

    zhdem = []
    if status == "associaciya":
        zhdem = [raund["vedushiy"]]
    elif status == "otvety":
        sdali_loginy = [h["login"] for h in hody]
        zhdem = [i["login"] for i in igroki if i["login"] not in sdali_loginy]
    elif status == "golosovanie":
        golosovali = [g["login"] for g in golosa]
        zhdem = [
            i["login"] for i in igroki
            if i["login"] not in golosovali and i["login"] != raund["vedushiy"]
        ]
    elif status == "itogi":
        zhdem = [i["login"] for i in igroki if not i["gotov"]]
    otvet["zhdem"] = zhdem

    if status in ("golosovanie", "itogi"):
        otvet["karty_na_stole"] = [
            {"karta": h["karta"], "moya": h["login"] == login}
            for h in hody
        ]
    else:
        otvet["karty_na_stole"] = []

    if status == "itogi":
        otvet["itogi"] = database.itogi_raunda(kod, raund["nomer"])
    else:
        otvet["itogi"] = []

    return JSONResponse(otvet)