#-*- coding: utf-8 -*-

'''
    Ultimate Whitecream
    Copyright (C) 2015 mortael

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import urllib, urllib2, re, cookielib, os.path, sys, socket, time, tempfile, string
import xbmc, xbmcplugin, xbmcgui, xbmcaddon, sqlite3, urlparse, xbmcvfs, base64

from jsunpack import unpack

from StringIO import StringIO
import gzip

__scriptname__ = "SerienStream"
__author__ = "mortael"
__scriptid__ = "plugin.video.serienstream"
__credits__ = "mortael, Fr33m1nd, anton40, NothingGnome"
__version__ = "1.1.18"

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'

headers = {'User-Agent': USER_AGENT,
           'Accept': '*/*',
           'Connection': 'keep-alive'}
           
openloadhdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}           

addon_handle = int(sys.argv[1])
addon = xbmcaddon.Addon(id=__scriptid__)

progress = xbmcgui.DialogProgress()
dialog = xbmcgui.Dialog()

rootDir = addon.getAddonInfo('path')
if rootDir[-1] == ';':
    rootDir = rootDir[0:-1]
rootDir = xbmc.translatePath(rootDir)
resDir = os.path.join(rootDir, 'resources')
imgDir = os.path.join(resDir, 'images')
uwcicon = xbmc.translatePath(os.path.join(rootDir, 'icon.png'))

profileDir = addon.getAddonInfo('profile')
profileDir = xbmc.translatePath(profileDir).decode("utf-8")
cookiePath = os.path.join(profileDir, 'cookies.lwp')

if not os.path.exists(profileDir):
    os.makedirs(profileDir)

urlopen = urllib2.urlopen
cj = cookielib.LWPCookieJar()
Request = urllib2.Request

if cj != None:
    if os.path.isfile(xbmc.translatePath(cookiePath)):
        try:
            cj.load(xbmc.translatePath(cookiePath))
        except:
            try:
                os.remove(xbmc.translatePath(cookiePath))
                pass
            except:
                dialog.ok('Oh oh','The Cookie file is locked, please restart Kodi')
                pass
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
else:
    opener = urllib2.build_opener()

urllib2.install_opener(opener)

favoritesdb = os.path.join(profileDir, 'favorites.db')

class StopDownloading(Exception):
    def __init__(self, value): self.value = value 
    def __str__(self): return repr(self.value)

def downloadVideo(url, name):

    def _pbhook(downloaded, filesize, url=None,dp=None):
        try:
            percent = min((downloaded*100)/filesize, 100)
            currently_downloaded = float(downloaded) / (1024 * 1024)
            kbps_speed = int(downloaded / (time.clock() - start))
            if kbps_speed > 0:
                eta = (filesize - downloaded) / kbps_speed
            else:
                eta = 0
            kbps_speed = kbps_speed / 1024
            total = float(filesize) / (1024 * 1024)
            mbs = '%.02f MB of %.02f MB' % (currently_downloaded, total)
            e = 'Speed: %.02f Kb/s ' % kbps_speed
            e += 'ETA: %02d:%02d' % divmod(eta, 60) 
            dp.update(percent,'',mbs,e)
        except:
            percent = 100
            dp.update(percent)
        if dp.iscanceled():
            dp.close()
            raise StopDownloading('Stopped Downloading')

            
    def getResponse(url, headers2, size):
        try:
            if size > 0:
                size = int(size)
                headers2['Range'] = 'bytes=%d-' % size

            req = Request(url, headers=headers2)

            resp = urlopen(req, timeout=30)
            return resp
        except:
            return None    

    def doDownload(url, dest, dp):

        try: headers = dict(urlparse.parse_qsl(url.rsplit('|', 1)[1]))
        except: headers = dict('')
        
        if 'openload' in url:
            headers = openloadhdr

        url = url.split('|')[0]
        file = dest.rsplit(os.sep, 1)[-1]
        resp = getResponse(url, headers, 0)

        if not resp:
            xbmcgui.Dialog().ok("Ultimate Whitecream", 'Download failed', 'No response from server')
            return False

        try:    content = int(resp.headers['Content-Length'])
        except: content = 0

        try:    resumable = 'bytes' in resp.headers['Accept-Ranges'].lower()
        except: resumable = False

        #print "Download Header"
        #print resp.headers
        if resumable:
            print "Download is resumable"

        if content < 1:
            xbmcgui.Dialog().ok("Ultimate Whitecream", 'Unknown filesize', 'Unable to download')
            return False

        size = 8192
        mb   = content / (1024 * 1024)

        if content < size:
            size = content

        total   = 0
        errors  = 0
        count   = 0
        resume  = 0
        sleep   = 0

        print 'Download File Size : %dMB %s ' % (mb, dest)

        #f = open(dest, mode='wb')
        f = xbmcvfs.File(dest, 'w')

        chunk  = None
        chunks = []

        while True:
            downloaded = total
            for c in chunks:
                downloaded += len(c)
            percent = min(100 * downloaded / content, 100)

            _pbhook(downloaded,content,url,dp)

            chunk = None
            error = False

            try:        
                chunk  = resp.read(size)
                if not chunk:
                    if percent < 99:
                        error = True
                    else:
                        while len(chunks) > 0:
                            c = chunks.pop(0)
                            f.write(c)
                            del c

                        f.close()
                        print '%s download complete' % (dest)
                        return True

            except Exception, e:
                print str(e)
                error = True
                sleep = 10
                errno = 0

                if hasattr(e, 'errno'):
                    errno = e.errno

                if errno == 10035: # 'A non-blocking socket operation could not be completed immediately'
                    pass

                if errno == 10054: #'An existing connection was forcibly closed by the remote host'
                    errors = 10 #force resume
                    sleep  = 30

                if errno == 11001: # 'getaddrinfo failed'
                    errors = 10 #force resume
                    sleep  = 30

            if chunk:
                errors = 0
                chunks.append(chunk)
                if len(chunks) > 5:
                    c = chunks.pop(0)
                    f.write(c)
                    total += len(c)
                    del c

            if error:
                errors += 1
                count  += 1
                print '%d Error(s) whilst downloading %s' % (count, dest)
                xbmc.sleep(sleep*1000)

            if (resumable and errors > 0) or errors >= 10:
                if (not resumable and resume >= 50) or resume >= 500:
                    #Give up!
                    print '%s download canceled - too many error whilst downloading' % (dest)
                    return False

                resume += 1
                errors  = 0
                if resumable:
                    chunks  = []
                    #create new response
                    print 'Download resumed (%d) %s' % (resume, dest)
                    resp = getResponse(url, headers, total)
                else:
                    #use existing response
                    pass
    

    def clean_filename(s):
        if not s:
            return ''
        badchars = '\\/:*?\"<>|\''
        for c in badchars:
            s = s.replace(c, '')
        return s;            

    download_path = addon.getSetting('download_path')
    if download_path == '':
        try:
            download_path = xbmcgui.Dialog().browse(0, "Download Path", 'myprograms', '', False, False)
            addon.setSetting(id='download_path', value=download_path)
            if not os.path.exists(download_path):
                os.mkdir(download_path)
        except:
            pass
    if download_path != '':
        dp = xbmcgui.DialogProgress()
        name = name.split("[")[0]
        dp.create("Ultimate Whitecream Download",name[:50])
        tmp_file = tempfile.mktemp(dir=download_path, suffix=".mp4")
        tmp_file = xbmc.makeLegalFilename(tmp_file)        
        start = time.clock()
        try:
            #urllib.urlretrieve(url,tmp_file,lambda nb, bs, fs, url=url: _pbhook(nb,bs,fs,url,dp))
            downloaded = doDownload(url, tmp_file, dp)
            if downloaded:
                vidfile = xbmc.makeLegalFilename(download_path + clean_filename(name) + ".mp4")
                try:
                  os.rename(tmp_file, vidfile)
                  return vidfile
                except:
                  return tmp_file
            else: raise StopDownloading('Stopped Downloading')
        except:
            while os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                    break
                except:
                    pass


def notify(header=None, msg='', duration=5000):
    if header is None: header = 'Ultimate Whitecream'
    builtin = "XBMC.Notification(%s,%s, %s, %s)" % (header, msg, duration, uwcicon)
    xbmc.executebuiltin(builtin)


def PLAYVIDEO(url, name, download=None):
    progress.create('Play video', 'Searching videofile.')
    progress.update( 10, "", "Loading video page", "" )
    videosource = getHtml(url, url)
    playvideo(videosource, name, download, url)


def playvideo(videosource, name, download=None, url=None):
    hosts = []
    if re.search('vivo\.sx/', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('Vivo')
    if re.search('videomega\.tv/', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('VideoMega')
    if re.search('openload\.(?:co|io)?/', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('OpenLoad')
    if re.search('streamin\.to/', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('Streamin')          
    if re.search('flashx\.tv/', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('FlashX')
    if re.search('mega3x\.net/', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('Mega3X')
    if re.search('streamcloud\.eu/', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('StreamCloud')
    if re.search('jetload\.tv/', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('Jetload')
    if re.search('videowood\.tv/', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('Videowood')
    if re.search('streamdefence.com/view\.php', videosource, re.DOTALL | re.IGNORECASE):
        hosts.append('Streamdefence')        
    if not url == None and not 'keeplinks' in url:
        if re.search('keeplinks\.eu/p1', videosource, re.DOTALL | re.IGNORECASE):
            hosts.append('Keeplinks <--')        
    if len(hosts) == 0:
        progress.close()
        notify('Oh oh','Couldn\'t find any video')
        return
    elif len(hosts) > 1:
        if addon.getSetting("dontask") == "true":
            vidhost = hosts[0]            
        else:
            vh = dialog.select('Videohost:', hosts)
            vidhost = hosts[vh]
    else:
        vidhost = hosts[0]
    
    if vidhost == 'Vivo':
        videourl = playvideoUrlResolver(videosource, r"//vivo\.sx/([0-9a-zA-Z-_]+)", 'http://vivo.sx/%s')
    if vidhost == 'VideoMega':
        progress.update( 40, "", "Loading videomegatv", "" )
        if re.search("videomega.tv/iframe.js", videosource, re.DOTALL | re.IGNORECASE):
            hashref = re.compile("""javascript["']>ref=['"]([^'"]+)""", re.DOTALL | re.IGNORECASE).findall(videosource)
        elif re.search("videomega.tv/iframe.php", videosource, re.DOTALL | re.IGNORECASE):
            hashref = re.compile(r"iframe\.php\?ref=([^&]+)&", re.DOTALL | re.IGNORECASE).findall(videosource)
        elif re.search("videomega.tv/view.php", videosource, re.DOTALL | re.IGNORECASE):
            hashref = re.compile(r'view\.php\?ref=([^"]+)', re.DOTALL | re.IGNORECASE).findall(videosource)
        elif re.search("videomega.tv/cdn.php", videosource, re.DOTALL | re.IGNORECASE):
            hashref = re.compile(r'cdn\.php\?ref=([^"]+)', re.DOTALL | re.IGNORECASE).findall(videosource)
        elif re.search("videomega.tv/\?ref=", videosource, re.DOTALL | re.IGNORECASE):
            hashref = re.compile(r'videomega.tv/\?ref=([^"]+)', re.DOTALL | re.IGNORECASE).findall(videosource)
        else:
            hashkey = re.compile("""hashkey=([^"']+)""", re.DOTALL | re.IGNORECASE).findall(videosource)
            if not hashkey:
                notify('Oh oh','Couldn\'t find playable videomega link')
                return
            hashkey = chkmultivids(hashkey)
            hashpage = getHtml('http://videomega.tv/validatehash.php?hashkey='+hashkey, url)
            hashref = re.compile('ref="([^"]+)', re.DOTALL | re.IGNORECASE).findall(hashpage)
        progress.update( 80, "", "Getting video file from Videomega", "" )
        vmhost = 'http://videomega.tv/view.php?ref=' + hashref[0]
        videopage = getHtml(vmhost, url)
        vmpacked = re.compile(r"(eval\(.*\))\s+</", re.DOTALL | re.IGNORECASE).findall(videopage)
        vmunpacked = unpack(vmpacked[0])
        videourl = re.compile('src",\s?"([^"]+)', re.DOTALL | re.IGNORECASE).findall(vmunpacked)
        videourl = videourl[0]
        videourl = videourl + '|Referer=' + vmhost + '&User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25'
    elif vidhost == 'OpenLoad':
        progress.update( 40, "", "Loading Openload", "" )
        openloadurl = re.compile(r"//(?:www\.)?openload\.(?:co|io)?/(?:embed|f)/([0-9a-zA-Z-_]+)", re.DOTALL | re.IGNORECASE).findall(videosource)
        openloadurl = chkmultivids(openloadurl)
        
        openloadurl1 = 'http://openload.co/f/%s/' % openloadurl

        try:
            openloadsrc = getHtml(openloadurl1, '', openloadhdr)
            progress.update( 80, "", "Getting video file from OpenLoad", "")
            videourl = decodeOpenLoad(openloadsrc)
            videourl = videourl + '|Referer='+ openloadurl1 + '&User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25'
        except:
            notify('Oh oh','Couldn\'t find playable OpenLoad link')
            return
    elif vidhost == 'Streamin':
        progress.update( 40, "", "Loading Streamin", "" )
        streaminurl = re.compile(r"//(?:www\.)?streamin\.to/(?:embed-)?([0-9a-zA-Z]+)", re.DOTALL | re.IGNORECASE).findall(videosource)
        streaminurl = chkmultivids(streaminurl)
        streaminurl = 'http://streamin.to/embed-%s-670x400.html' % streaminurl
        streaminsrc = getHtml2(streaminurl)
        videohash = re.compile('\?h=([^"]+)', re.DOTALL | re.IGNORECASE).findall(streaminsrc)
        videourl = re.compile('image: "(http://[^/]+/)', re.DOTALL | re.IGNORECASE).findall(streaminsrc)
        progress.update( 80, "", "Getting video file from Streamin", "" )
        videourl = videourl[0] + videohash[0] + "/v.mp4"
    elif vidhost == 'FlashX':
        progress.update( 40, "", "Loading FlashX", "" )
        flashxurl = re.compile(r"//(?:www\.)?flashx\.tv/(?:embed-)?([0-9a-zA-Z]+)", re.DOTALL | re.IGNORECASE).findall(videosource)
        flashxurl = chkmultivids(flashxurl)       
        flashxurl = 'http://flashx.tv/embed-%s-670x400.html' % flashxurl
        flashxsrc = getHtml2(flashxurl)
        progress.update( 60, "", "Grabbing video file", "" )
        flashxurl2 = re.compile('<a href="([^"]+)"', re.DOTALL | re.IGNORECASE).findall(flashxsrc)
        flashxsrc2 = getHtml(flashxurl2[0])
        progress.update( 70, "", "Grabbing video file", "" ) 
        flashxjs = re.compile("<script type='text/javascript'>([^<]+)</sc", re.DOTALL | re.IGNORECASE).findall(flashxsrc2)
        progress.update( 80, "", "Getting video file from FlashX", "" )
        try: flashxujs = unpack(flashxjs[0])
        except: flashxujs = flashxjs[0]
        videourl = re.compile(r'\[\{\s*?file:\s*?"([^"]+)",', re.DOTALL | re.IGNORECASE).findall(flashxujs)
        videourl = videourl[-1]
    elif vidhost == 'Mega3X':
        progress.update( 40, "", "Loading Mega3X", "" )
        mega3xurl = re.compile(r"(https?://(?:www\.)?mega3x.net/(?:embed-)?(?:[0-9a-zA-Z]+).html)", re.DOTALL | re.IGNORECASE).findall(videosource)
        mega3xurl = chkmultivids(mega3xurl)
        mega3xsrc = getHtml(mega3xurl,'', openloadhdr)
        mega3xjs = re.compile("<script[^>]+>(eval[^<]+)</sc", re.DOTALL | re.IGNORECASE).findall(mega3xsrc)
        progress.update( 80, "", "Getting video file from Mega3X", "" )
        mega3xujs = unpack(mega3xjs[0])
        videourl = re.compile('file:\s?"([^"]+mp4)"', re.DOTALL | re.IGNORECASE).findall(mega3xujs)
        videourl = videourl[0]  
    elif vidhost == 'StreamCloud':
        progress.update( 40, "", "Opening Streamcloud", "" )
        streamcloudurl = re.compile(r"//(?:www\.)?streamcloud\.eu?/([0-9a-zA-Z-_/.]+html)", re.DOTALL | re.IGNORECASE).findall(videosource)
        streamcloudurl = chkmultivids(streamcloudurl)        
        streamcloudurl = "http://streamcloud.eu/" + streamcloudurl
        progress.update( 50, "", "Getting Streamcloud page", "" )
        schtml = postHtml(streamcloudurl)
        form_values = {}
        match = re.compile('<input.*?name="(.*?)".*?value="(.*?)">', re.DOTALL | re.IGNORECASE).findall(schtml)
        for name, value in match:
            form_values[name] = value.replace("download1","download2")
        progress.update( 60, "", "Grabbing video file", "" )    
        newscpage = postHtml(streamcloudurl, form_data=form_values)
        videourl = re.compile('file: "(.+?)",', re.DOTALL | re.IGNORECASE).findall(newscpage)[0]
    elif vidhost == 'Jetload':
        progress.update( 40, "", "Loading Jetload", "" )
        jlurl = re.compile(r'jetload\.tv/([^"]+)', re.DOTALL | re.IGNORECASE).findall(videosource)
        jlurl = chkmultivids(jlurl)
        jlurl = "http://jetload.tv/" + jlurl
        jlsrc = getHtml(jlurl, url)
        videourl = re.compile(r'file: "([^"]+)', re.DOTALL | re.IGNORECASE).findall(jlsrc)
        videourl = videourl[0]
    elif vidhost == 'Videowood':
        progress.update( 40, "", "Loading Videowood", "" )
        vwurl = re.compile(r"//(?:www\.)?videowood\.tv/(?:embed|video)/([0-9a-zA-Z]+)", re.DOTALL | re.IGNORECASE).findall(videosource)
        vwurl = chkmultivids(vwurl)
        vwurl = 'http://www.videowood.tv/embed/' + vwurl
        vwsrc = getHtml(vwurl, url)
        progress.update( 80, "", "Getting video file from Videowood", "" )
        videourl = videowood(vwsrc)
    elif vidhost == 'Keeplinks <--':
        progress.update( 40, "", "Loading Keeplinks", "" )
        klurl = re.compile(r"//(?:www\.)?keeplinks\.eu/p1/([0-9a-zA-Z]+)", re.DOTALL | re.IGNORECASE).findall(videosource)
        klurl = chkmultivids(klurl)
        klurl = 'http://www.keeplinks.eu/p1/' + klurl
        kllink = getVideoLink(klurl, '')
        kllinkid = kllink.split('/')[-1]
        klheader = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
           'Accept-Encoding': 'none',
           'Accept-Language': 'en-US,en;q=0.8',
           'Connection': 'keep-alive',
           'Cookie': 'flag['+kllinkid+'] = 1;'} 
        klpage = getHtml(kllink, klurl, klheader)
        playvideo(klpage, name, download, klurl)
        return
    elif vidhost == 'Streamdefence':
        progress.update( 40, "", "Loading Streamdefence", "" )
        sdurl = re.compile(r'streamdefence\.com/view.php\?ref=([^"]+)"', re.DOTALL | re.IGNORECASE).findall(videosource)
        sdurl = chkmultivids(sdurl)
        sdurl = 'http://www.streamdefence.com/view.php?ref=' + sdurl
        sdsrc = getHtml(sdurl, url)
        progress.update( 80, "", "Getting video file from Streamdefence", "" )
        sdpage = streamdefence(sdsrc)
        playvideo(sdpage, name, download, sdurl)
        return
    progress.close()
    playvid(videourl, name, download)


def playvid(videourl, name, download=None):
    if download == 1:
        downloadVideo(videourl, name)
    else:
        iconimage = xbmc.getInfoImage("ListItem.Thumb")
        listitem = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
        listitem.setInfo('video', {'Title': name, 'Genre': 'Porn'})
        xbmc.Player().play(videourl, listitem)


def chkmultivids(videomatch):
    videolist = list(set(videomatch))
    if len(videolist) > 1:
        i = 1
        hashlist = []
        for x in videolist:
            hashlist.append('Video ' + str(i))
            i += 1
        mvideo = dialog.select('Multiple videos found', hashlist)
        return videolist[mvideo]
    else:
        return videomatch[0]


def PlayStream(name, url):
    item = xbmcgui.ListItem(name, path = url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)
    return


def getHtml(url, referer='', hdr=None, NoCookie=None, data=None):
    if not hdr:
        req = Request(url, data, headers)
    else:
        req = Request(url, data, hdr)
    if len(referer) > 1:
        req.add_header('Referer', referer)
    if data:
        req.add_header('Content-Length', len(data))
    response = urlopen(req, timeout=60)
    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO( response.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
        f.close()
    else:
        data = response.read()    
    if not NoCookie:
        # Cope with problematic timestamp values on RPi on OpenElec 4.2.1
        try:
            cj.save(cookiePath)
        except: pass
    response.close()
    return data

    
def postHtml(url, form_data={}, headers={}, compression=True):
    _user_agent = 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.1 ' + \
                  '(KHTML, like Gecko) Chrome/13.0.782.99 Safari/535.1'
    req = urllib2.Request(url)
    if form_data:
        form_data = urllib.urlencode(form_data)
        req = urllib2.Request(url, form_data)
    req.add_header('User-Agent', _user_agent)
    for k, v in headers.items():
        req.add_header(k, v)
    if compression:
        req.add_header('Accept-Encoding', 'gzip')
    response = urllib2.urlopen(req)
    data = response.read()
    cj.save(cookiePath)
    response.close()
    return data

    
def getHtml2(url):
    req = Request(url)
    response = urlopen(req, timeout=60)
    data = response.read()
    response.close()
    return data 

    
def getVideoLink(url, referer):
    req2 = Request(url, '', headers)
    req2.add_header('Referer', referer)
    url2 = urlopen(req2).geturl()
    return url2


def cleantext(text):
    text = text.replace('&#8211;','-')
    text = text.replace('&#038;','&')
    text = text.replace('&#8217;','\'')
    text = text.replace('&#8216;','\'')
    text = text.replace('&#8230;','...')
    text = text.replace('&quot;','"')
    text = text.replace('&#039;','`')
    text = text.replace('&amp;','&')
    text = text.replace('&ntilde;','ñ')
    return text


def addDownLink(name, url, mode, iconimage, desc, stream=None, fav='add', noDownload=False):
    contextMenuItems = []
    if fav == 'add': favtext = "Add to"
    elif fav == 'del': favtext = "Remove from"
    u = (sys.argv[0] +
         "?url=" + urllib.quote_plus(url) +
         "&mode=" + str(mode) +
         "&name=" + urllib.quote_plus(name))
    dwnld = (sys.argv[0] +
         "?url=" + urllib.quote_plus(url) +
         "&mode=" + str(mode) +
         "&download=" + str(1) +
         "&name=" + urllib.quote_plus(name))
    favorite = (sys.argv[0] +
         "?url=" + urllib.quote_plus(url) +
         "&fav=" + fav +
         "&favmode=" + str(mode) +
         "&mode=" + str('900') +
         "&img=" + urllib.quote_plus(iconimage) +
         "&name=" + urllib.quote_plus(name))         
    ok = True
    liz = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setArt({'thumb': iconimage, 'icon': iconimage})
    fanart = os.path.join(rootDir, 'fanart.jpg')
    if addon.getSetting('posterfanart') == 'true':
        fanart = iconimage
        liz.setArt({'poster': iconimage})
    liz.setArt({'fanart': fanart})
    if stream:
        liz.setProperty('IsPlayable', 'true')
    if len(desc) < 1:
        liz.setInfo(type="Video", infoLabels={"Title": name})
    else:
        liz.setInfo(type="Video", infoLabels={"Title": name, "plot": desc, "plotoutline": desc})
    contextMenuItems.append(('[COLOR hotpink]' + favtext + ' favorites[/COLOR]', 'xbmc.RunPlugin('+favorite+')'))
    if noDownload == False:
        contextMenuItems.append(('[COLOR hotpink]Download Video[/COLOR]', 'xbmc.RunPlugin('+dwnld+')'))
    liz.addContextMenuItems(contextMenuItems, replaceItems=False)
    ok = xbmcplugin.addDirectoryItem(handle=addon_handle, url=u, listitem=liz, isFolder=False)
    return ok
    

def addDir(name, url, mode, iconimage, page=None, channel=None, section=None, keyword='', Folder=True):
    u = (sys.argv[0] +
         "?url=" + urllib.quote_plus(url) +
         "&mode=" + str(mode) +
         "&page=" + str(page) +
         "&channel=" + str(channel) +
         "&section=" + str(section) +
         "&keyword=" + urllib.quote_plus(keyword) +
         "&name=" + urllib.quote_plus(name))
    ok = True
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setArt({'thumb': iconimage, 'icon': iconimage})
    fanart = os.path.join(rootDir, 'fanart.jpg')
    if addon.getSetting('posterfanart') == 'true':
        fanart = iconimage
        liz.setArt({'poster': iconimage})
    liz.setArt({'fanart': fanart})
    liz.setInfo(type="Video", infoLabels={"Title": name})
    ok = xbmcplugin.addDirectoryItem(handle=addon_handle, url=u, listitem=liz, isFolder=Folder)
    return ok
    
def _get_keyboard(default="", heading="", hidden=False):
    """ shows a keyboard and returns a value """
    keyboard = xbmc.Keyboard(default, heading, hidden)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return unicode(keyboard.getText(), "utf-8")
    return default
 
 
def decodeOpenLoad(html):

    # decodeOpenLoad made by mortael, please leave this line for proper credit :)
    aastring = re.compile("<script[^>]+>(ﾟωﾟﾉ[^<]+)<", re.DOTALL | re.IGNORECASE).findall(html)
    #haha = re.compile(r"welikekodi_ya_rly = (\d+) - (\d+)", re.DOTALL | re.IGNORECASE).findall(html)
    #haha = int(haha[0][0]) - int(haha[0][1])

    #if haha == 1:
    #    haha2 = 2
    #else:
    #    haha2 = 1
    
    videourl1 = decodeOpenLoad2(aastring[0])
    #videourl2 = decodeOpenLoad2(aastring[haha2])

    #xbmc.log(videourl1)
    #xbmc.log(videourl2)
    return videourl1
    
    
def decodeOpenLoad2(aastring):
    aastring = aastring.replace("(ﾟДﾟ)[ﾟεﾟ]+(oﾟｰﾟo)+ ((c^_^o)-(c^_^o))+ (-~0)+ (ﾟДﾟ) ['c']+ (-~-~1)+","")
    aastring = aastring.replace("((ﾟｰﾟ) + (ﾟｰﾟ) + (ﾟΘﾟ))", "9")
    aastring = aastring.replace("((ﾟｰﾟ) + (ﾟｰﾟ))","8")
    aastring = aastring.replace("((ﾟｰﾟ) + (o^_^o))","7")
    aastring = aastring.replace("((o^_^o) +(o^_^o))","6")
    aastring = aastring.replace("((ﾟｰﾟ) + (ﾟΘﾟ))","5")
    aastring = aastring.replace("(ﾟｰﾟ)","4")
    aastring = aastring.replace("((o^_^o) - (ﾟΘﾟ))","2")
    aastring = aastring.replace("(o^_^o)","3")
    aastring = aastring.replace("(ﾟΘﾟ)","1")
    aastring = aastring.replace("(+!+[])","1")
    aastring = aastring.replace("(c^_^o)","0")
    aastring = aastring.replace("(0+0)","0")
    aastring = aastring.replace("(ﾟДﾟ)[ﾟεﾟ]","\\")
    aastring = aastring.replace("(3 +3 +0)","6")
    aastring = aastring.replace("(3 - 1 +0)","2")
    aastring = aastring.replace("(!+[]+!+[])","2")
    aastring = aastring.replace("(-~-~2)","4")
    aastring = aastring.replace("(-~-~1)","3")
    aastring = aastring.replace("(-~0)","1")
    aastring = aastring.replace("(-~1)","2")
    aastring = aastring.replace("(-~3)","4")
    aastring = aastring.replace("(0-0)","0")
    
    decodestring = re.search(r"\\\+([^(]+)", aastring, re.DOTALL | re.IGNORECASE).group(1)
    decodestring = "\\+"+ decodestring
    decodestring = decodestring.replace("+","")
    decodestring = decodestring.replace(" ","")
    
    decodestring = decode(decodestring)
    decodestring = decodestring.replace("\\/","/")
    
    if 'toString' in decodestring:
        base = re.compile(r"toString\(a\+(\d+)", re.DOTALL | re.IGNORECASE).findall(decodestring)[0]
        base = int(base)
        match = re.compile(r"(\(\d[^)]+\))", re.DOTALL | re.IGNORECASE).findall(decodestring)
        for repl in match:
            match1 = re.compile(r"(\d+),(\d+)", re.DOTALL | re.IGNORECASE).findall(repl)
            base2 = base + int(match1[0][0])
            repl2 = base10toN(int(match1[0][1]),base2)
            decodestring = decodestring.replace(repl,repl2)
        decodestring = decodestring.replace("+","")
        decodestring = decodestring.replace("\"","")
        #xbmc.log(decodestring)
        videourl = re.search(r"(http[^\}]+)", decodestring, re.DOTALL | re.IGNORECASE).group(1)
        videourl = videourl.replace("https","http")
    else:
        videourl = re.search(r"vr\s?=\s?\"|'([^\"']+)", decodestring, re.DOTALL | re.IGNORECASE).group(1)
        
    UA = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:39.0) Gecko/20100101 Firefox/39.0'
    headers = {'User-Agent': UA }
    
    req = urllib2.Request(videourl,None,headers)
    res = urllib2.urlopen(req)
    videourl = res.geturl()
    
    
    return videourl

def decode(encoded):
    for octc in (c for c in re.findall(r'\\(\d{2,3})', encoded)):
        encoded = encoded.replace(r'\%s' % octc, chr(int(octc, 8)))
    return encoded.decode('utf8')


def base10toN(num,n):
    num_rep={10:'a',
         11:'b',
         12:'c',
         13:'d',
         14:'e',
         15:'f',
         16:'g',
         17:'h',
         18:'i',
         19:'j',
         20:'k',
         21:'l',
         22:'m',
         23:'n',
         24:'o',
         25:'p',
         26:'q',
         27:'r',
         28:'s',
         29:'t',
         30:'u',
         31:'v',
         32:'w',
         33:'x',
         34:'y',
         35:'z'}
    new_num_string=''
    current=num
    while current!=0:
        remainder=current%n
        if 36>remainder>9:
            remainder_string=num_rep[remainder]
        elif remainder>=36:
            remainder_string='('+str(remainder)+')'
        else:
            remainder_string=str(remainder)
        new_num_string=remainder_string+new_num_string
        current=current/n
    return new_num_string


# videowood decode copied from: https://github.com/schleichdi2/OpenNfr_E2_Gui-5.3/blob/4e3b5e967344c3ddc015bc67833a5935fc869fd4/lib/python/Plugins/Extensions/MediaPortal/resources/hosters/videowood.py    
def videowood(data):
    parse = re.search('(....ωﾟ.*?);</script>', data)
    if parse:
        todecode = parse.group(1).split(';')
        todecode = todecode[-1].replace(' ','')

        code = {
            "(ﾟДﾟ)[ﾟoﾟ]" : "o",
            "(ﾟДﾟ) [return]" : "\\",
            "(ﾟДﾟ) [ ﾟΘﾟ]" : "_",
            "(ﾟДﾟ) [ ﾟΘﾟﾉ]" : "b",
            "(ﾟДﾟ) [ﾟｰﾟﾉ]" : "d",
            "(ﾟДﾟ)[ﾟεﾟ]": "/",
            "(oﾟｰﾟo)": '(u)',
            "3ﾟｰﾟ3": "u",
            "(c^_^o)": "0",
            "(o^_^o)": "3",
            "ﾟεﾟ": "return",
            "ﾟωﾟﾉ": "undefined",
            "_": "3",
            "(ﾟДﾟ)['0']" : "c",
            "c": "0",
            "(ﾟΘﾟ)": "1",
            "o": "3",
            "(ﾟｰﾟ)": "4",
            }
        cryptnumbers = []
        for searchword,isword in code.iteritems():
            todecode = todecode.replace(searchword,isword)
        for i in range(len(todecode)):
            if todecode[i:i+2] == '/+':
                for j in range(i+2, len(todecode)):
                    if todecode[j:j+2] == '+/':
                        cryptnumbers.append(todecode[i+1:j])
                        i = j
                        break
                        break
        finalstring = ''
        for item in cryptnumbers:
            chrnumber = '\\'
            jcounter = 0
            while jcounter < len(item):
                clipcounter = 0
                if item[jcounter] == '(':
                    jcounter +=1
                    clipcounter += 1
                    for k in range(jcounter, len(item)):
                        if item[k] == '(':
                            clipcounter += 1
                        elif item[k] == ')':
                            clipcounter -= 1
                        if clipcounter == 0:
                            jcounter = 0
                            chrnumber = chrnumber + str(eval(item[:k+1]))
                            item = item[k+1:]
                            break
                else:
                    jcounter +=1
            finalstring = finalstring + chrnumber.decode('unicode-escape')
        stream_url = re.search('=\s*(\'|")(.*?)$', finalstring)
        if stream_url:
            return stream_url.group(2)
    else:
        return


def streamdefence(html):
    if 'openload' in html:
        return html
    match = re.search(r'\("([^"]+)', html, re.DOTALL | re.IGNORECASE)
    if match:
        result = match.group()
        decoded = base64.b64decode(result)
    else:
        decoded = base64.b64decode(html)
    return streamdefence(decoded)
        
        
def searchDir(url, mode, page=None):
    conn = sqlite3.connect(favoritesdb)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM keywords")
        for (keyword,) in c.fetchall():
            name = '[COLOR deeppink]' + urllib.unquote_plus(keyword) + '[/COLOR]'
            addDir(name, url, mode, '', page=page, keyword=keyword)
    except: pass
    addDir('[COLOR hotpink]Add Keyword[/COLOR]', url, 902, '', '', mode, Folder=False)
    addDir('[COLOR hotpink]Clear list[/COLOR]', '', 903, '', Folder=False)
    xbmcplugin.endOfDirectory(addon_handle)

def newSearch(url, mode):
    vq = _get_keyboard(heading="Searching for...")
    if (not vq): return False, 0
    title = urllib.quote_plus(vq)
    addKeyword(title)
    xbmc.executebuiltin('Container.Refresh')
    #searchcmd = (sys.argv[0] +
    #     "?url=" + urllib.quote_plus(url) +
    #     "&mode=" + str(mode) +
    #     "&keyword=" + urllib.quote_plus(title))
    #xbmc.executebuiltin('xbmc.RunPlugin('+searchcmd+')')


def clearSearch():
    delKeyword()
    xbmc.executebuiltin('Container.Refresh')


def addKeyword(keyword):
    xbmc.log(keyword)
    conn = sqlite3.connect(favoritesdb)
    c = conn.cursor()
    c.execute("INSERT INTO keywords VALUES (?)", (keyword,))
    conn.commit()
    conn.close()


def delKeyword():
    conn = sqlite3.connect(favoritesdb)
    c = conn.cursor()
    c.execute("DELETE FROM keywords;")
    conn.commit()
    conn.close()
