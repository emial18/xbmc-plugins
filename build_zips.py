""" addons.xml generator """

import os
import errno
import md5
import shutil
import zipfile
from xml.dom.minidom import parse

EXCLUDE_EXTS = ['.pyc', '.pyo', '.swp']

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise
		
def generateZip(ADDON):
	# Parse addon.xml for version number
	dom = parse("%s/addon.xml" % ADDON)
	addon = dom.getElementsByTagName('addon')[0]
	version = addon.getAttribute('version')
	zfilename = "%s-%s.zip" % (ADDON, version)
	
	mkdir_p("repo/" + ADDON)
	# Walk the directory to create the zip file
	z = zipfile.ZipFile("repo/" + ADDON + "/" + zfilename, 'w')
	for r, d, f in os.walk(ADDON):
	  for ff in f:
		skip = False

		# If it's not one of the files we're excluding
		for ext in EXCLUDE_EXTS:
		  if ff.endswith(ext):
			skip = True

		if not skip: 
		  z.write(os.path.join(r, ff), os.path.join(r, ff))
	z.close()
	
	if (os.path.isfile( ADDON + "/icon.png")):
		shutil.copy(ADDON+"/icon.png", "repo/" + ADDON)
	if (os.path.isfile( ADDON + "/fanart.jpg")):
		shutil.copy(ADDON+"/fanart.jpg", "repo/" + ADDON)



#ADDON='plugin.audio.afl-radio'

addons = os.listdir( "." )
for ADDON in addons:
	if ( not os.path.isdir( ADDON ) or ADDON == ".svn" or ADDON == ".git"): continue
	if ( not os.path.isfile( ADDON + "/addon.xml")): continue
	generateZip(ADDON)

#if ( __name__ == "__main__" ):
#    # start
#    Generator()