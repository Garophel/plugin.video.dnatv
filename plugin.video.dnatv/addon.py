import sys
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import time
import json
import re
from dnatv import DNATVSession

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])
settings = xbmcaddon.Addon(id='plugin.video.dnatv')

username = settings.getSetting('username')
password = settings.getSetting('password')
servicename = settings.getSetting('servicename')
last_refresh = int(settings.getSetting('lastRecordingsRefresh'))

xbmcplugin.setContent(addon_handle, 'movies')

def build_url(query):
	return base_url + '?' + urllib.urlencode(query)

def add_logout_context_menu_item(li):
	argsLogout = username + ', ' + password + ', ' + servicename + ', ' + '-logout' + ', '
	logout = 'XBMC.RunScript(special://home/addons/plugin.video.dnatv/dnatv.py, ' + argsLogout + ')'
	li.addContextMenuItems([(settings.getLocalizedString(30011), logout)])
	return li

def build_li(recording, folder, title=None):
	start_time = recording['startTime'].split()
	s_time = time.strptime(recording['startTime'][:-6], '%a, %d %b %Y %H:%M:%S')
	startDate = '%02d' % (s_time[2]) + '.' + '%02d' % (s_time[1]) + '.'  + str(s_time[0])
	if folder:
		li = xbmcgui.ListItem(title + ' (' + startDate + ')',iconImage='DefaultFolder.png')
		li.setInfo('video', { 'Date' : startDate})
		add_logout_context_menu_item( li )
	else:
		li = xbmcgui.ListItem(recording['title'],iconImage = 'DefaultFile.png')
		li.setInfo('video', { 'StartTime': start_time[4] , 'Date' : startDate,
			'title' : recording['title'],'Plot' : recording['description']})
		li.setProperty('IsPlayable', 'true')
		argsDelete = username + ', ' + password + ', ' + servicename + ', ' + '-delete' + ', ' + recording['programUid']
		deleteRecording = 'XBMC.RunScript(special://home/addons/plugin.video.dnatv/dnatv.py, ' + argsDelete + ')'
		argsDownload = username + ', ' + password + ', ' + servicename + ', ' + '-download' + ', ' + recording['programUid']
		downloadRecording = 'XBMC.RunScript(special://home/addons/plugin.video.dnatv/dnatv.py, ' + argsDownload + ')'
		argsLogout = username + ', ' + password + ', ' + servicename + ', ' + '-logout' + ', '
		logout = 'XBMC.RunScript(special://home/addons/plugin.video.dnatv/dnatv.py, ' + argsLogout + ')'
		li = add_logout_context_menu_item( li )
		li.addContextMenuItems([
			(settings.getLocalizedString(30007), deleteRecording),
			(settings.getLocalizedString(30008), downloadRecording),
			(settings.getLocalizedString(30009), 'Container.Refresh'),
			(settings.getLocalizedString(30011), logout)
			])
	return li

def main_dir():

	url = build_url({'foldername': 'liveTV'})
	li = xbmcgui.ListItem(label = settings.getLocalizedString(30005), iconImage = 'DefaultFolder.png')
	add_logout_context_menu_item( li )
	xbmcplugin.addDirectoryItem(handle = addon_handle, url = url, listitem = li, isFolder = True)

	url = build_url({'foldername': 'recordings'})
	li = xbmcgui.ListItem(label = settings.getLocalizedString(30006), iconImage = 'DefaultFolder.png')
	add_logout_context_menu_item( li )
	xbmcplugin.addDirectoryItem(handle = addon_handle, url = url, listitem = li, isFolder = True)

	xbmcplugin.endOfDirectory(addon_handle)

def recordings_dir():

	isnewlist = False

	# First check if the recording list is refreshed within two minutes and load it only if it's not
	if int(time.time())- last_refresh > 120:
		isnewlist = True
		dnatv = DNATVSession(username, password, servicename)
		if dnatv.login():
			recordings = dnatv.getrecordings()
			if recordings is None:
				xbmc.executebuiltin('XBMC.Notification(' + settings.getLocalizedString(30055) + ', )')
				sys.exit()
			settings.setSetting( id='lastRecordingsRefresh', value=str(int(time.time())))
			settings.setSetting( id='recordingList', value=json.dumps(recordings))

	else:
		recordings = json.loads(settings.getSetting( id='recordingList'))

	seriescandidates = []
	recordtitles = []
	serieslist = []
	title_re = re.compile('[:(]')
	index=0
	
	for recording in recordings:
		recording['order'] = index
		index += 1
		short_title = title_re.split(recording['title'])[0].strip()
		if short_title in serieslist:
			continue
		if short_title in recordtitles:
			serieslist.append(short_title)
		try:
			if not recording['recordings'][0]['status'] == 'RECORDED':
				continue
		except IndexError:
			continue
		else:
			recordtitles.append(short_title)
			seriescandidates.append(recording)

	serieslist = set(serieslist)
	removable = set()
	for i in serieslist:
		for j in serieslist:
			if j.startswith(i+' ') and (i != j):
				removable.add(j)

	serieslist = list(serieslist.difference(removable))

	serieslist.sort()
	settings.setSetting( id='seriestitles', value=json.dumps(serieslist))
	existingfolders = []

	for recording in seriescandidates:
		xbmc.log(recording['title'].encode('utf-8') + ' ' + recording['startTime'].encode('utf-8'))
		for seriestitle in serieslist:
			if (re.match(seriestitle + r'\b',recording['title']) or
				re.match(seriestitle + r'\s',recording['title'])):
					if not seriestitle in existingfolders:
						existingfolders.append(seriestitle)
						url = build_url({'foldername': serieslist.index(seriestitle)})
						li = build_li(recording, True, seriestitle)
						xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
						break

	recordings = sorted(recordings, key=lambda k: k['title'])
	seriesindex = 0
	seriesmember = False

	for recording in recordings:
		try:
			if not recording['recordings'][1]['status'] == 'RECORDED':
				continue
		except IndexError:
			continue
		while True:
			if (re.match(serieslist[seriesindex] + r'\b',recording['title']) or
				re.match(serieslist[seriesindex] + r'\s',recording['title'])):
				seriesmember = True
				recording['series'] = serieslist[seriesindex]
				break
			if seriesmember:
				seriesmember = False
				if seriesindex + 1 < len(serieslist):
					seriesindex = seriesindex+1
			else:
				break
		if not seriesmember:
			url = build_url({'mode': 'watch', 'videoUrl': recording['recordings'][1]['stream']['streamUrl']})
			li = build_li(recording, False)
			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)

	if isnewlist:
		recordings = sorted(recordings, key=lambda k: k['order'])
		settings.setSetting( id='recordingList', value=json.dumps(recordings))
	xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
	xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
	xbmcplugin.endOfDirectory(addon_handle)

def subdir():
	recordings = json.loads(settings.getSetting( id='recordingList'))
	serieslist = json.loads(settings.getSetting( id='seriestitles'))
	index = int(args.get('foldername')[0])
	seriestitle = serieslist[index]

	for recording in recordings:
		try:
			if not recording['recordings'][0]['status'] == 'RECORDED':
				continue
		except IndexError:
			continue
		try:
			if not recording['series'] == seriestitle :
				continue
		except KeyError:
			continue
		try:
			url = build_url({'mode': 'watch', 'videoUrl': recording['recordings'][1]['stream']['streamUrl']})
		except IndexError:
			continue
		li = build_li(recording,False)
		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)

	xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
	xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
	xbmcplugin.endOfDirectory(addon_handle)

def livetv_dir():
	dnatv = DNATVSession(username, password, servicename)
	if dnatv.login():
		liveTV = dnatv.getlivetv()
		if liveTV is None:
			xbmc.executebuiltin('XBMC.Notification(' + settings.getLocalizedString(30055) + ', )')
			sys.exit()
		for channel in liveTV:
			if not channel['isUserAuthorized']:
				continue
			try:
				url = build_url({'mode': 'watch', 'videoUrl': channel['liveService']['services'][0]['stream']['streamUrl']})
			except IndexError:
				continue
			li = xbmcgui.ListItem(channel['title'], iconImage='DefaultFile.png')
			start_time = channel['epg'][0]['startTime'].split()
			li.setInfo('video', { 'StartTime': start_time[4],
				'Plot' : channel['epg'][0]['title'] + '\n' + channel['epg'][0]['description']})
			li.setProperty('IsPlayable', 'true')
			add_logout_context_menu_item( li )
			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
		xbmcplugin.endOfDirectory(addon_handle)	
	
def watch_program():
	videoUrl = args.get('videoUrl', None)
	dnatv = DNATVSession(username, password, servicename)
	if dnatv.login():
		url = dnatv.getplayableurl(videoUrl[0]).headers.get('location')
		title = args.get('title', None)
		listitem = xbmcgui.ListItem(title)
		listitem.setInfo('video', {'Title': title})
		listitem.setPath(url)
		xbmcplugin.setResolvedUrl(handle=addon_handle, succeeded=True, listitem=listitem)

def main():
	mode = args.get('mode', None)
	folder = args.get('foldername', None)
	if mode != None:
		if mode[0] == 'watch':
			watch_program()
	if folder != None:
		if folder[0] == 'recordings':
			recordings_dir()
		
		elif folder[0] == 'liveTV':
			livetv_dir()
		
		else:
			subdir()
	else:
		main_dir()

main()
