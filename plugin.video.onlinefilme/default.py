#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib,  urllib2, re, os, sys, string
import xbmc, xbmcplugin,xbmcgui,xbmcaddon, onlinefilme

pluginhandle = int(sys.argv[1])

addon = xbmcaddon.Addon(id='plugin.video.onlinefilme')

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

if mode == 'MOVIE':    onlinefilme.getCategories("http://onlinefilme.to", "filme-online")
if mode == 'SERIES':   onlinefilme.getCategories("http://onlinefilme.to", "serie-online")
if mode == 'CATEGORY': onlinefilme.getCategory(url)
if mode == 'PLAY':     onlinefilme.play(url, name)
elif mode == None:     onlinefilme.getCategories("http://onlinefilme.to", "filme-online")
