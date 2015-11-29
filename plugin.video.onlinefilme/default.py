#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib,  urllib2, re, os, sys, string
import xbmc, xbmcplugin,xbmcgui,xbmcaddon

sys.path.append( os.path.join(xbmcaddon.Addon(id='script.module.urlresolver').getAddonInfo( 'path' ), 'lib') )
sys.path.append( os.path.join(xbmcaddon.Addon(id='script.module.t0mm0.common').getAddonInfo( 'path' ), 'lib') )

import urlresolver

headers  = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) ; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET4.0C)'
}
pluginhandle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.onlinefilme')

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
    item = xbmcgui.ListItem("Filme")
    uri = sys.argv[0] + '?mode=MOVIE'
    xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)

    item = xbmcgui.ListItem("Serien")
    uri = sys.argv[0] + '?mode=SERIES'
    xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)

    xbmcplugin.endOfDirectory(pluginhandle, True)

def getCategories(url, mode):
    print "getCategories: " + url + " mode: " + mode
    html = GET(url)
    match = re.compile('<a href="http://onlinefilme.to/' + mode + '(.*?)"><strong>(.+?)</strong></a>').findall(html)
    for link, name in match:
        item = xbmcgui.ListItem(name)
        uri = sys.argv[0] + '?mode=CATEGORY' + '&url=http://onlinefilme.to/' + mode + link
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.endOfDirectory(pluginhandle, True)

def getCategory(url):
    print "getCategory: " + url
    html = GET(url)
    match = re.compile('<a href="(.+?)">\s+<div class="movie-holder">\s+<div class="image-wrapper">\s+<div class="image">\s+<img data-original="(.+?)" title="(.+?)"', re.UNICODE).findall(html)
    for link, thumb, name in match:
        item = xbmcgui.ListItem(name)
        uri = sys.argv[0] + '?mode=PLAY&url=' + link
        item.setIconImage('http://onlinefilme.to/' + thumb)
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)

    match = re.compile("<li class='current'><a href='javascript:void\(0\)'>.+?</a></li><li><a href='(.+?)'>").findall(html)
    for nexturl in match:
        item = xbmcgui.ListItem("Weiter >>")
        uri = sys.argv[0] + '?mode=CATEGORY&url=' + nexturl
        xbmcplugin.addDirectoryItem(pluginhandle, uri, item, True)
    xbmcplugin.endOfDirectory(pluginhandle, True)

def play(url):
    print "play: " + url
    html = GET(url)
    match = re.compile("<a href='(.+?)' target='_blank' class='button small radius expand'>Weiter</a>").findall(html)
    print match
    sources = []
    for videopage in match:
        redirect = REDIRECT(videopage)
        host = redirect.replace('http://', '')
        host = host[:host.index('/')]
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
        listitem = xbmcgui.ListItem(name)
        listitem.setPath(stream_url)
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
    img=params['img']
except: pass
try:
    name=params['name']
except: pass
try:
    url=urllib.unquote_plus(params['url'])
except: pass

if mode == 'MOVIE':
    getCategories("http://onlinefilme.to", "filme-online")
if mode == 'SERIES':
    getCategories("http://onlinefilme.to", "serie-online")
if mode == 'CATEGORY':
    getCategory(url)
if mode == 'PLAY':
    play(url)
elif mode == None:
    getCategories("http://onlinefilme.to", "filme-online")
