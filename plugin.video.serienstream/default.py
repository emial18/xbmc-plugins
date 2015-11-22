#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib,  urllib2, re, os, sys, string
import xbmc, xbmcplugin,xbmcgui,xbmcaddon

sys.path.append( os.path.join(xbmcaddon.Addon(id='script.module.urlresolver').getAddonInfo( 'path' ), 'lib') )
sys.path.append( os.path.join(xbmcaddon.Addon(id='script.module.t0mm0.common').getAddonInfo( 'path' ), 'lib') )
sys.path.append( os.path.join(xbmcaddon.Addon(id='script.module.beautifulsoup').getAddonInfo( 'path' ), 'lib') )

import urlresolver
import BeautifulSoup

headers  = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) ; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET4.0C)'
}
pluginhandle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.serienstream')

def GET(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0')
    response = urllib2.urlopen(req, timeout = 30)
    link = response.read()
    response.close()
    return link

def REDIRECT(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0')
    response = urllib2.urlopen(req, timeout = 30)
    redirect = response.geturl()
    response.close()
    return redirect

def getIndex():
    for char in string.ascii_uppercase:
        item = xbmcgui.ListItem(char)
        uri = sys.argv[0] + '?mode=CATALOG' + '&url=http://serienstream.to/katalog/' + char
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)

    item = xbmcgui.ListItem('0-9')
    uri = sys.argv[0] + '?mode=CATALOG' + '&url=http://serienstream.to/katalog/0-9'
    xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)

    xbmcplugin.endOfDirectory(pluginhandle, True)

def getCatalog(url):
    print "getCatalog: " + url
    html = GET(url)
    soup = BeautifulSoup.BeautifulSoup(html)
    series = soup.find('ul', attrs = { 'class': 'search_box_list' })
    for elem in series.findAll('li'):
        link = elem.find('a')['href']
        item = xbmcgui.ListItem(str(elem.find('h3')).replace('<h3>','').replace('</h3>',''))
        img = elem.find('img')['src']
        item.setIconImage(img)
        uri = sys.argv[0] + '?mode=SERIES' + '&url=' + link + "&img=" + img
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.endOfDirectory(pluginhandle, True)

def addSeriesMetadata(url, item):
    print "addSeriesMetadata: " + url
    html = GET(url)
    print "match: " , match

def getSeries(url, img):
    print "getSeries: " + url
    html = GET(url)
    match = re.compile('<a href="(.+?staffel.+?)".+?>([0-9]+?)</a>').findall(html)
    for videopage, season in match:
        item = xbmcgui.ListItem('Staffel ' + season)
        match2 = re.compile('<p itemprop="description">(.+?)</p>', re.DOTALL).findall(html)
        plot = match2[0]
        match2 = re.compile('class="genreButton clearbutton" itemprop="genre">(.+?)</a>').findall(html)
        genre = match2[0]
        match2 = re.compile('<div class="backdrop" style="background-image: url\((.+?)\)"></div>').findall(html)
        backdrop = match2[0]
        item.setArt({ 'poster': img, 'fanart' : backdrop })
        item.setInfo('video', { 'genre': genre, 'plot': plot, 'plotoutline' : plot })
        item.setIconImage(img)
        uri = sys.argv[0] + '?mode=SEASON' + '&url=' + videopage + "&season=" + season + "&img=" + img
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.setContent(pluginhandle, 'tvshows')
    xbmc.executebuiltin('Container.SetViewMode(504)')
    xbmcplugin.endOfDirectory(pluginhandle, True)

def getSeason(url, season, img):
    print "getSeason: " + url + " Season: " + season
    html = GET(url)
    soup = BeautifulSoup.BeautifulSoup(html)
    series = soup.find('table', attrs = { 'class': 'seasonEpisodesList' })
    for elem in series.findAll('tr'):
        try:
            match = re.compile('Folge ([0-9]+).+?<td class="seasonEpisodeTitle">.+?<a href="(.+?)">.+?<strong>(.+?)</strong>', re.DOTALL).findall(str(elem))
            name = match[0][0] + " - " + match[0][2]
            item = xbmcgui.ListItem(name)
            item.setIconImage(img)
            uri = sys.argv[0] + '?mode=PLAY' + '&url=' + match[0][1] + "&name=" + name
            xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
        except: pass
    xbmcplugin.endOfDirectory(pluginhandle, True)

def play(url, name):
    print "play: " + url + " Name: " + name
    html = GET(url)
    match = re.compile('<i class="icon .+?"></i>\n\s+(.+?)\s+<a href="(.+?)"\n\s+target="_blank">').findall(html)
    sources = []
    for host, videopage in match:
        redirect = REDIRECT(videopage)
        sources.append(urlresolver.HostedMediaFile(url=redirect, title=host))

    if (len(sources)==0):
        xbmc.executebuiltin("XBMC.Notification(Sorry!,Show doesn't have playable links,5000)")
    else:
        source = urlresolver.choose_source(sources)
        if source:
            xbmc.executebuiltin("XBMC.Notification(Please Wait!,Resolving Link,3000)")
            stream_url = source.resolve()
        else:
            return
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
        listitem = xbmcgui.ListItem("foo")
        listitem.setPath(stream_url)
        #listitem.setInfo('video', {'Title': mname, 'Plot': descs} )
        playlist.add(stream_url,listitem)
        xbmc.Player().play(playlist)
        return True

def get_params(paramstring):
    param=[]
    if len(paramstring)>=2:
        params=paramstring
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]
    if len(param) > 0:
        for cur in param:
            param[cur] = urllib.unquote_plus(param[cur])
    return param

url=None
mode=None

print sys.argv
params = get_params(sys.argv[2])

try:
    mode=params['mode'].upper()
except: pass
try:
    season=params['season'].upper()
except: pass
try:
    img=params['img']
except: pass
try:
    name=params['name']
except: pass
try:
    url=urllib.unquote_plus(params['url'])
except: pass

if mode == 'CATALOG':
    getCatalog(url)
if mode == 'SERIES':
    getSeries(url, img)
if mode == 'SEASON':
    getSeason(url, season, img)
if mode == 'PLAY':
    play(url, name)
elif mode == None:
    getIndex()
