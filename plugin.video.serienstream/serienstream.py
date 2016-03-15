#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib, urllib2, re, os, sys
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import utils

pluginhandle = int(sys.argv[1])

UNSUPPORTED_HOSTS = [ 'NowVideo', 'Shared', 'FileNuke', 'CloudTime', 'PowerWatch', 'YouWatch' ] # ['Vivo']

addon = xbmcaddon.Addon(id='plugin.video.serienstream')

def GET(url):
    print "serienstream::GET " + url
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0')
    response = urllib2.urlopen(req, timeout = 30)
    link = response.read()
    response.close()
    return link

def REDIRECT(url):
    print "serienstream::REDIRECT " + url
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0')
    response = urllib2.urlopen(req, timeout = 30)
    redirect = response.geturl()
    response.close()
    return redirect

def REFRESH(url):
    print "serienstream::REFRESH " + url
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0')
    response = urllib2.urlopen(req, timeout = 30)
    html = response.read()
    response.close()
    link = re.compile('<meta http-equiv="refresh" content="0; url=(.+?)" />', re.DOTALL).findall(html)[0]
    print "  Found link: " + link
    return link
    
def getIndex():
    html = GET('http://serienstream.to/serien')
    match = re.compile('<li><a href="(http://serienstream.to/genre/.+?)">(.+?)</a>').findall(html)
    for url, category in match:
        item = xbmcgui.ListItem(category)
        uri = sys.argv[0] + '?mode=CATEGORY' + '&url=' + url
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.endOfDirectory(pluginhandle, True)

def getCategory(url):
    print "getCatalog: " + url
    html = GET(url)
    match = re.compile('<a href="(http://serienstream.to/serie/stream/.+?)".+?<img.+?src="(.+?)".+?<h3>(.+?)</h3>', re.DOTALL).findall(html)
    for link, img, title in match:
        item = xbmcgui.ListItem(title)
        item.setIconImage(img)
        uri = sys.argv[0] + '?mode=SERIES' + '&url=' + link + "&img=" + img
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
    match = re.compile('<a href="(.+?)" target="_blank">\s+<i class="icon (.+?)" title=Icon .+?"></i>').findall(html)
    sources = ""
    for videopage, host in match:
        if not host in UNSUPPORTED_HOSTS:
            sources = sources + videopage + "\n"
    print "Found sources: " + sources
    if (len(sources)==0):
        xbmc.executebuiltin("XBMC.Notification(Sorry!,Show doesn't have playable links,5000)")
    else:
        utils.playvideo(sources, name)
