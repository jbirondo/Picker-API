from datetime import datetime
from bs4 import BeautifulSoup
import requests
import pandas
import os
import flask
import flask_cors
from flask import request, jsonify, json
from flask_cors import CORS

app = flask.Flask(__name__)
app.config["DEBUG"] = False

CORS(app, supports_credentials=True)

def get_main_data():
    r = requests.get("https://www.vegasinsider.com/nfl/odds/las-vegas/", headers={
                    'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'})
    c = r.content
    soup = BeautifulSoup(c, "html.parser")
    all = soup.find_all("table", {"class": "frodds-data-tbl"})
    weatherr = requests.get("https://rotogrinders.com/weather/nfl", headers={
                            'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'})
    weatherc = weatherr.content
    weathersoup = BeautifulSoup(weatherc, "html.parser")
    weatherall = weathersoup.find_all("div", {"class": "crd"})
    weatherd = {}
    for tab in weatherall:
        teams = [x.text.replace(" ", "_")
                 for x in tab.find_all("span", {"class": "lng"})]
        for i in range(0, 2):
            if teams[i] == "New_York":
                teams[i] = "N.Y._" + \
                    [x.text for x in tab.find_all("span", {"class": "mascot"})][i]
            if teams[i] == "Los_Angeles":
                teams[i] = "L.A._" + \
                    [x.text for x in tab.find_all("span", {"class": "mascot"})][i]
        weathertable = [x.text for x in tab.find_all("span", {"class": "display"})]
        weathertable = weathertable[1:3] + weathertable[4:]
        if len(weathertable) > 1:
            weatherd[teams[1].replace(" ", "_")] = {
                "Temperature": weathertable[0],
                "Precipitation": weathertable[1],
                "Wind Direction": weathertable[2],
                "Wind Speed": weathertable[3]
            }
        else:
            weatherd[teams[1].replace(" ", "_")] = {
                "Temperature": "Dome",
                "Precipitation": "Dome",
                "Wind Direction": "Dome",
                "Wind Speed": "Dome"
            }
    table = all[0].find_all("tr")
    l = []
    for a in table[:len(weatherd)]:
        d = {}
        teams = [x.text.replace(" ", "_") for x in a.find_all("b")]
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
        d["Precipitation"] = weatherd[teams[1]]["Precipitation"]
        d["Wind Direction"] = weatherd[teams[1]]["Wind Direction"]
        d["Wind Speed"] = weatherd[teams[1]]["Wind Speed"]
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
            p["Injury"] = arr[4]
            p["Injury Summary"] = " ".join(arr[5:])
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
