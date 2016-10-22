#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib, urllib2, re, os, sys, time
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import utils

pluginhandle = int(sys.argv[1])

UNSUPPORTED_HOSTS = [ 'NowVideo', 'Shared', 'FileNuke', 'CloudTime', 'PowerWatch', 'YouWatch' ] # ['Vivo']

addon = xbmcaddon.Addon(id='plugin.video.serienstream')
sys.path.append(os.path.join(addon.getAddonInfo('path'), "lib" ) )

cloudfareSupport = addon.getSetting("cloudfare")

import cfscrape

def notify(header=None, msg='', duration=5000):
    if header is None: header = 'SerienStream.to'
    builtin = "XBMC.Notification(%s,%s, %s, %s)" % (header, msg, duration, xbmc.translatePath(os.path.join(addon.getAddonInfo('path'), 'icon.png')))
    xbmc.executebuiltin(builtin)

def update_cloudfare():
    if not cloudfareSupport:
        return "", 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0'
    filename = os.path.join(xbmc.translatePath(addon.getAddonInfo('profile')), 'cloudfare.txt')
    if os.path.isfile(filename) and (time.time() - os.path.getmtime(filename) < 3600):
        f = open(filename,'r')
        content = [x.strip('\n') for x in f.readlines()]
        f.close()
        cookie_value = content[0]
        user_agent = content[1]
        return cookie_value, user_agent
    else:
        notify("Okay", "Get Cloudflare token")
        cookie_value, user_agent = cfscrape.get_cookie_string("https://serienstream.to")
        f = open(filename,'w')
        f.write(cookie_value + '\n')
        f.write(user_agent + '\n')
        f.close()
        return cookie_value, user_agent

def GET(url):
    print "serienstream::GET " + url
    try:
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0')
        #req.add_header('User-Agent', user_agent)
        #req.add_header('Cookie', cookie_value)
        response = urllib2.urlopen(req, timeout = 30)
        link = response.read()
        response.close()
        return link
    except Exception as e:
        notify("Oh oh", e)
        return ""

def REDIRECT(url):
    print "serienstream::REDIRECT " + url
    try:
        req = urllib2.Request(url)
        req.add_header('User-Agent', user_agent)
        req.add_header('Cookie', cookie_value)
        response = urllib2.urlopen(req, timeout = 30)
        redirect = response.geturl()
        response.close()
        return redirect
    except:
        notify("Oh oh", "")
        return ""

def REFRESH(url):
    print "serienstream::REFRESH " + url
    try:
        req = urllib2.Request(url)
        req.add_header('User-Agent', user_agent)
        req.add_header('Cookie', cookie_value)
        response = urllib2.urlopen(req, timeout = 30)
        html = response.read()
        response.close()
        link = re.compile('<meta http-equiv="refresh" content="0; url=(.+?)" />', re.DOTALL).findall(html)[0]
        print "  Found link: " + link
        return link
    except:
        notify("Oh oh", "")
        return ""

def ADD_ENTRY(name, category, url):
    item = xbmcgui.ListItem(name)
    uri = sys.argv[0] + '?mode=' + category + '&url=' + url
    xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
        
def getIndex():
    ADD_ENTRY('Genres', 'GENRES', 'none')
    ADD_ENTRY('Neu', 'CATEGORY', 'http://serienstream.to/#neu')
    ADD_ENTRY('Beliebt', 'CATEGORY', 'http://serienstream.to/#beliebt')
    xbmcplugin.endOfDirectory(pluginhandle, True)   
        
def getGenres():
    html = GET('http://serienstream.to/')
    match = re.compile('<a title=".+?".+?href="http://serienstream.to/genre/(.+?)">(.+?)</a>', re.DOTALL).findall(html)
    for url, category in match:
        item = xbmcgui.ListItem(category)
        uri = sys.argv[0] + '?mode=CATEGORY' + '&url=http://serienstream.to/genre/' + url
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.endOfDirectory(pluginhandle, True)

def getCategory(url):
    print "getCatalog: " + url
    html = GET(url)
    match = re.compile('<a href="/serie/stream/(.+?)".+?title=".+?">.+?<img.+?src="(.+?)".+?title=".+?".+?alt=".+?">.+?<h3>(.+?)<span', re.DOTALL).findall(html)
    for link, img, title in match:
        item = xbmcgui.ListItem(title)
        item.setIconImage(img)
        uri = sys.argv[0] + '?mode=SERIES' + '&url=http://serienstream.to/serie/stream/' + link + "&img=http://serienstream.to/" + img
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.endOfDirectory(pluginhandle, True)

def getSeries(url, img):
    print "getSeries: " + url
    html = GET(url)
    match = re.compile('<a.+?href="(.+?staffel-[0-9]+)".+?>([0-9]+?)</a>').findall(html)
    reDescription = re.compile('data-full-description="(.+?)"', re.DOTALL)
    reBackground = re.compile('<div class="backdrop" style="background-image: url\((.+?)\)"></div>')
    for videopage, season in match:
        item = xbmcgui.ListItem('Staffel ' + season)
        plot = reDescription.findall(html)[0]
        backdrop = reBackground.findall(html)[0]
        item.setArt({ 'poster': img, 'fanart' : backdrop })
        item.setInfo('video', { 'plot': plot, 'plotoutline' : plot })
        item.setIconImage(img)
        uri = sys.argv[0] + '?mode=SEASON' + '&url=http://serienstream.to' + videopage + "&season=" + season + "&img=" + img
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.setContent(pluginhandle, 'tvshows')
    xbmc.executebuiltin('Container.SetViewMode(504)')
    xbmcplugin.endOfDirectory(pluginhandle, True)

def getSeason(url, season, img):
    print "getSeason: " + url + " Season: " + season
    html = GET(url)
    match = re.compile('<td class="seasonEpisodeTitle">.+?<a href="(.+?)">.+?<strong>(.*?)</strong>(.+?)</td>', re.DOTALL).findall(html)
    reSeason = re.compile('staffel-([0-9]+)/episode-([0-9]+)')
    reRemain = re.compile('<span>(.+?)</span>')
    for uri, name, remain in match:
        mRemain = reRemain.findall(remain)
        if len(mRemain) > 0:
            name = name + " (" + mRemain[0] + ")"
        m = reSeason.findall(uri)
        season = '%02d' % int(m[0][0])
        episode = '%02d' % int(m[0][1])
        item = xbmcgui.ListItem("S" + season + "E" + episode + " " + name)
        item.setIconImage(img)
        uri = sys.argv[0] + '?mode=PLAY' + '&url=http://serienstream.to' + uri + "&name=" + name
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.endOfDirectory(pluginhandle, True)

def play(url, name):
    print "play: " + url + " Name: " + name
    utils.progress.create('Play video', 'Searching videofile.')
    utils.progress.update( 10, "", "Loading video page", "" )
    html = GET(url)
    match = re.compile('<li class="col-md-4.+?<a href="(.+?)" target="_blank">.+?<i class="icon (.+?)"', re.DOTALL).findall(html)
    sources = ""
    for videopage, host in match:
        if not host in UNSUPPORTED_HOSTS:
            sources = sources + videopage + "\n"
    print "Found sources: " + sources
    if (len(sources)==0):
        xbmc.executebuiltin("XBMC.Notification(Sorry!,Show doesn't have playable links,5000)")
    else:
        utils.playvideo(sources, name)

#cookie_value, user_agent = update_cloudfare()
