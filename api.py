from datetime import datetime
from bs4 import BeautifulSoup
import requests
import pandas
import os
import flask
import flask_cors
from flask import request, jsonify, json
from flask_cors import CORS
import unicodedata

app = flask.Flask(__name__)
app.config["DEBUG"] = False

CORS(app, supports_credentials=True)

def get_main_data():
    r = requests.get("https://www.vegasinsider.com/nfl/odds/las-vegas/", headers={
                    'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'})
    c = r.content
    soup = BeautifulSoup(c, "html.parser")
    all = soup.find_all("table", {"class": "frodds-data-tbl"})
    weatherr = requests.get("https://www.vegasinsider.com/nfl/weather/", headers={
                            'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'})


    weatherc = weatherr.content
    weathersoup = BeautifulSoup(weatherc, "html.parser")

    first_table = weathersoup.find("tbody")
    games_table = first_table.find("tbody")
    games = games_table.find_all("tr")
    games = games[1:-1]

    weatherd = {}
    for game in games:
        teams = ["_".join(x.text.strip().split()[:-1]) if x.text.strip()
                != "Washington Football Team" else "Washington" for x in game.find_all("b")]
        for i in range(0, 2):
            if teams[i] == "Los_Angeles":
                teams[i] = "L.A._" + game.find_all("b")[i].text.strip().split()[-1]
            if teams[i] == "New_York":
                teams[i] = "N.Y._" + game.find_all("b")[i].text.strip().split()[-1]
        weathertable = [x.text.replace("\n", "").replace(
            "\r", "").replace("\t", "") for x in game.find_all("td")]
        heat_index = unicodedata.normalize("NFKC", weathertable[2:][-1])
        humidity = unicodedata.normalize("NFKC", weathertable[2:][-2])
        temperature = unicodedata.normalize(
            "NFKC", weathertable[2:][-3]) if unicodedata.normalize("NFKC", weathertable[2:][-3]) != " " else "DOME"
        wind = unicodedata.normalize("NFKC", weathertable[2:][-4]).split()
        wind_direction = " ".join(wind[:-1]) if wind else "DOME"
        wind_speed = "{} MPH".format(wind[-1].replace(".", "")) if wind else "DOME"
        summary = unicodedata.normalize("NFKC", weathertable[2]) if weathertable[2] != "\xa0" else "NO SUMMARY"
        weatherd[teams[1]] = {
            "Summary": summary,
            "Wind Direction": wind_direction,
            "Wind Speed": wind_speed,
            "Temperature": temperature,
            "Humidity": humidity,
            "Heat Index": heat_index
        }


    table = all[0].find_all("tr")[:len(weatherd)]
    l = []
    for a in table:
        d = {}
        teams = [x.text.replace(" ", "_") for x in a.find_all("b")]
        if teams[1] not in weatherd.keys():
            continue
        odds = a.find_all("td", {"class": "oddsCell"})
        o = odds[1].find_all("a")
        ol = []
        for x in o[0].childGenerator():
            if str(type(x)) == "<class 'bs4.element.NavigableString'>":
                ol.append(str(x))
        ol1 = [x.replace(u"\xa0", " ") for x in ol[1:]]
        ol2 = [x.replace(u"\n\t\t\t\t\t\t\t", "") for x in ol1]
        for x in range(0, 2):
            if x == 0 and ol2[x][0] != "-":
                d["Over/Under"] = ol2[x]
                d["Favorite"] = teams[1]
                d["Underdog"] = teams[0]
            if x == 1 and ol2[x][0] != "-":
                d["Over/Under"] = ol2[x]
                d["Favorite"] = teams[0]
                d["Underdog"] = teams[1]

        d["Away"] = teams[0]
        d["Home"] = teams[1]
        d["Date/Time"] = a.find("span", {"class": "cellTextHot"}).text
        d["Temperature"] = weatherd[teams[1]]["Temperature"]
        d["Wind Direction"] = weatherd[teams[1]]["Wind Direction"]
        d["Wind Speed"] = weatherd[teams[1]]["Wind Speed"]
        d["Weather Summary"] = weatherd[teams[1]]["Summary"]
        l.append(d)
    sortedArray = sorted(
        l,
        key=lambda x: datetime.strptime(x['Date/Time'], '%m/%d %H:%M %p')
    )
    return sortedArray

def get_injury_data():
    injr = requests.get("https://www.cbssports.com/nfl/injuries/", headers={
        'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'})
    injc = injr.content
    injsoup = BeautifulSoup(injc, "html.parser")
    injall = injsoup.find_all("div", {"class": "TableBaseWrapper"})
    injd = {}
    days = ["Sun,", "Mon,", "Tue,", "Wed,", "Thu,", "Fri,", "Sat,"]
    for team in injall:
        teamname = team.find("span", {"class": "TeamName"}).text.strip().replace(" ", "_")
        injd[teamname] = []
        for player in team.find_all("tr", {"class": "TableBase-bodyTr"}):
            p = {}
            day = [a for a in player.text.strip().replace(
                "\n", "").split() if a in days]
            i = player.text.strip().replace("\n", "").split().index(day[0]) - 1
            arr = player.text.strip().replace("\n", "").split()[i:]
            p["Name"] = player.find(
                "span", {"class": "CellPlayerName--long"}).text.replace("\n", "")
            p["Position"] = arr[0]
            p["Date of Injury"] = " ".join(arr[1:4])
            p["Injury"] = player.find("td", {"style": " width: 20%;"}).text.strip().replace("\n", "")
            p["Injury Summary"] = player.find(
                "td", {"style": " min-width: 200px; width: 40%;"}).text.strip().replace("\n", "")
            injd[teamname].append(p)
        injd[teamname] = sorted(injd[teamname], key=lambda x: datetime.strptime(
            x['Date of Injury'], '%a, %b %d'), reverse=True)
    
    return injd




@app.route('/', methods=['GET'])
def home():
    return '{"MatchUps": ' + str(get_main_data()) + "}"

@app.route('/<away>-<home>')
def matchup(away, home):
    return {
        "Away": get_injury_data()[away], 
        "Home": get_injury_data()[home], 
        "MatchUp": list(filter(lambda x: x['Home'] == home, get_main_data()))[0]
        }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
