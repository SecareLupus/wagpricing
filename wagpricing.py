from bottle import Bottle, run
import requests
from bs4 import BeautifulSoup
import re

app = Bottle()

@app.route('/search/<cardname>')
def search(cardname):
    result = getMTGStocksSearchHTML(cardname, False)
    resultSoup = BeautifulSoup(result)
    del(result)
    status = getSearchResultStatus(resultSoup)
    if status['searchResultStatus'] == 'SINGLE_VERSION':
        status['resolvedName'] = getCardNameFromSoup(resultSoup)
        status['medPrice'] = getMedianPriceFromSoup(resultSoup)
        status['resolvedSet'] = getCardSetFromSoup(resultSoup)
    if status['searchResultStatus'] == 'PLURAL_VERSIONS':
        status['resolvedName'] = getCardNameFromSoup(resultSoup)
        tmpVersions = getPossibleVersionsFromSoup(resultSoup)
        found_set = getCardSetFromSoup(resultSoup)
        print("Found the set to be: " + found_set)
        linkedurl = urlFromLocalRoute(tmpVersions[0][0])
        print("Found first object to be: [" + tmpVersions[0][0] + ", " + tmpVersions[0][1] + "]")
        linkedSoup = getSoupFromUrl(linkedurl)
        found_at = getSpecificVersionUrlFromSoup(linkedSoup, found_set)
        print("Found the url to be: " + found_at)
        tmpVersions.append([found_at, found_set])
        status['possibleCards'] = tmpVersions
        del(linkedSoup)
    if status['searchResultStatus'] == 'PLURAL_MATCHES':
        status['possibleCards'] = getPossibleCardNamesFromSoup(resultSoup)
    if status['searchResultStatus'] == 'NO_MATCHES':
        pass
    if status['searchResultStatus'] == 'ERROR':
        pass

    del(resultSoup)
    return status

@app.route('/search/<cardname>/<setname>')
def resolve(cardname, setname):
    resultSoup = getMTGStocksSearchHTML(cardname)
    status = getSearchResultStatus(resultSoup)
    if status['searchResultStatus'] == 'SINGLE_VERSION':
        status['resolvedName'] = getCardNameFromSoup(resultSoup)
        status['resolvedSet'] = getCardSetFromSoup(resultSoup)
        status['medPrice'] = getMedianPriceFromSoup(resultSoup)
        if (status['resolvedSet'] != setname):
            del(status)
            status['searchResultStatus'] = 'BAD SET'
    if status['searchResultStatus'] == 'PLURAL_VERSIONS':
        status['resolvedName'] = getCardNameFromSoup(resultSoup)
        tmpVersions = getPossibleVersionsFromSoup(resultSoup)
        found_set = getCardSetFromSoup(resultSoup)
        if(found_set == setname):
            status['searchResultStatus'] = 'SINGLE_VERSION'
            status['resolvedSet'] = getCardSetFromSoup(resultSoup)
            status['medPrice'] = getMedianPriceFromSoup(resultSoup)
            return status
        for version in tmpVersions:
            if (version[1] == setname):
                status['searchResultStatus'] = 'SINGLE_VERSION'
                status['resolvedSet'] = setname
                status['medPrice'] = getMedianPriceFromUrl(urlFromLocalRoute(version[0]))
                return status
    if status['searchResultStatus'] == 'PLURAL_MATCHES':
        pass
    if status['searchResultStatus'] == 'NO_MATCHES':
        pass
    if status['searchResultStatus'] == 'ERROR':
        pass

    del(resultSoup)
    return status



@app.route('/url<address:path>')
def url(address):
    status = {'searchResultStatus' : 'SINGLE_VERSION'}
    status['medPrice'] = getMedianPriceFromUrl(urlFromLocalRoute(address))
    status['resolvedName'] = getCardNameFromUrl(urlFromLocalRoute(address))
    return status


def getMTGStocksSearchHTML(cardname, soup=True):
    print("Searching for " + cardname)
    payload = {
        'utf8': '?',
        'print[card]': cardname,
        'button': ''
    }
    r = requests.get('http://www.mtgstocks.com/cards/search', params=payload)
    rtext = r.text
    del(r)
    del(payload)
    if soup:
        return BeautifulSoup(rtext)
    return rtext


def getSearchResultStatus(htmlresponse):
    if htmlresponse.find(text=re.compile("No cards matched the provided search criteria")):
        return {'searchResultStatus': 'NO_MATCHES'}
    if htmlresponse.find(text=re.compile("Search Results")):
        return {'searchResultStatus': 'PLURAL_MATCHES'}
    if htmlresponse.find(text=re.compile("Other sets")):
        return {'searchResultStatus': 'PLURAL_VERSIONS'}
    if htmlresponse.find(text=re.compile("Data about this card")):
        return {'searchResultStatus': 'SINGLE_VERSION'}
    return {'searchResultStatus': 'ERROR'}


def getMedianPriceFromUrl(url):
    return getMedianPriceFromHTML(requests.get(url).text)


def getMedianPriceFromHTML(html):
    r = BeautifulSoup(html)
    medPrice = getMedianPriceFromSoup(r)
    del(r)
    return medPrice


def getMedianPriceFromSoup(soup):
    tag = soup.find("div", class_="priceheader average")
    if (type(tag) is 'NoneType'):
        return ""
    return tag.string

def getPossibleCardNamesFromSoup(soup):
    possNames = soup.find("th", text=re.compile("Search Results"))
    possNames = possNames.parent.parent.parent
    possNames = possNames.select("a[href]")
    tmp = []
    subtmp = []
    for printme in possNames:
        url = printme['href']
        text = printme.string
        if url.find('cards') != -1:
            subtmp.append(url)
            subtmp.append(text)
        else:
            subtmp.append(text)
            tmp.append(subtmp)
            subtmp = []
    return tmp

def getSoupFromUrl(url):
    r = requests.get(url)
    return BeautifulSoup(r.text)

def getCardNameFromUrl(url):
    return getCardNameFromHtml(requests.get(url).text)

def getCardNameFromHtml(html):
    return getCardNameFromSoup(BeautifulSoup(html))

def getCardNameFromSoup(soup):
    tmp = soup.find("div", class_="col-md-7 col-sm-12")
    tmp = tmp.find("a").string
    return tmp

def getCardSetFromSoup(soup):
    tmp = soup.find("div", class_="col-md-7 col-sm-12")
    tmp = tmp.findAll("a")[1].string
    return tmp

def getSpecificVersionUrlFromSoup(soup, setName):
    allSets = getPossibleVersionsFromSoup(soup)
    for link in allSets:
        if (link[1] == setName):
            return link[0]
    return "null"

def getPossibleVersionsFromSoup(soup):
    possNames = soup.find("table", class_="table table-condensed table-striped")
    possNames = possNames.select("a[href]")

    tmp = []
    for printme in possNames:
        url = printme['href']
        text = printme.string
        tmp.append([url, text])
    return tmp


def urlFromLocalRoute(address):
    return "http://www.mtgstocks.com" + address


@app.route('/goodbye')
def goodbye():
    return 'Goodbye!'

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    }


def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c,c) for c in text)

def start_me():
    run(app, host='localhost', port=8080)