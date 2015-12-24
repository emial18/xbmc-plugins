#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib, urllib2, re, os, sys
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import utils

pluginhandle = int(sys.argv[1])

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
    match = re.compile('<a href="(.+?staffel.+?)".+?>([0-9]+?)</a>').findall(html)
    reDescription = re.compile('<p itemprop="description">(.+?)</p>', re.DOTALL)
    reBackground = re.compile('<div class="backdrop" style="background-image: url\((.+?)\)"></div>')
    for videopage, season in match:
        item = xbmcgui.ListItem('Staffel ' + season)
        plot = reDescription.findall(html)[0]
        backdrop = reBackground.findall(html)[0]
        item.setArt({ 'poster': img, 'fanart' : backdrop })
        item.setInfo('video', { 'plot': plot, 'plotoutline' : plot })
        item.setIconImage(img)
        uri = sys.argv[0] + '?mode=SEASON' + '&url=' + videopage + "&season=" + season + "&img=" + img
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
        uri = sys.argv[0] + '?mode=PLAY' + '&url=' + uri + "&name=" + name
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.endOfDirectory(pluginhandle, True)

def play(url, name):
    print "play: " + url + " Name: " + name
    utils.progress.create('Play video', 'Searching videofile.')
    utils.progress.update( 10, "", "Loading video page", "" )
    html = GET(url)
    match = re.compile('<i class="icon .+?"></i>\n\s+(.+?)\s+<a href="(.+?)"\n\s+target="_blank">').findall(html)
    sources = ""
    for host, videopage in match:
        if host != 'Vivo' and host != 'FileNuke' and host != 'CloudTime' and host != 'PowerWatch':
            redirect = REDIRECT(videopage)
            sources = sources + redirect + "\n"
    print sources
    if (len(sources)==0):
        xbmc.executebuiltin("XBMC.Notification(Sorry!,Show doesn't have playable links,5000)")
    else:
        utils.playvideo(sources, name)
