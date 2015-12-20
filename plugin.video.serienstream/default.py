#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib, urllib2, re, os, sys
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import utils
import serienstream

pluginhandle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.serienstream')

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

if mode == 'SEARCH':  serienstream.search()
if mode == 'CATEGORY': serienstream.getCategory(url)
if mode == 'SERIES':   serienstream.getSeries(url, img)
if mode == 'SEASON':   serienstream.getSeason(url, season, img)
if mode == 'PLAY':     serienstream.play(url, name)
elif mode == None:     serienstream.getIndex()
