import sys
import time
import urllib

import AddonSignals
import requests
import xbmc
import xbmcaddon
import xbmcgui

from addon_information import AddonInformation
from logger import Logger
from next_up_info import NextUpInfo
from post_play_info import PostPlayInfo
from library import LibraryFunctions
from still_watching_info import StillWatchingInfo
from unwatched_info import UnwatchedInfo
from utils import Utils

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json


# service class for playback monitoring
class Player(xbmc.Player):
    # Borg - multiple instances, shared state
    _shared_state = {}

    xbmcplayer = xbmc.Player()
    addon_info = AddonInformation()
    addon = addon_info.get_addon()

    logLevel = 0
    currenttvshowid = None
    currentepisodeid = None
    playedinarow = 1
    fields_base = '"dateadded", "file", "lastplayed","plot", "title", "art", "playcount",'
    fields_file = fields_base + '"streamdetails", "director", "resume", "runtime",'
    fields_tvshows = fields_base + '"sorttitle", "mpaa", "premiered", "year", "episode", "watchedepisodes", "votes", "rating", "studio", "season", "genre", "episodeguide", "tag", "originaltitle", "imdbnumber"'
    fields_episodes = fields_file + '"cast", "productioncode", "rating", "votes", "episode", "showtitle", "tvshowid", "season", "firstaired", "writer", "originaltitle"'
    postplaywindow = None
    dbserver = addon.getSetting("SkipDBServer")
    url = dbserver + "/index.php"

    def __init__(self, *args):
        self.__dict__ = self._shared_state
        self.logger = Logger("%s %s" % (self.addon_info.get_addon_name(), self.__class__.__name__))
        self.logMsg("Starting playback monitor service", 1)
        self.library = LibraryFunctions()

    def logMsg(self, msg, lvl=1):
        self.logger.log(msg, lvl)

    def onPlayBackStarted(self):
        # Will be called when xbmc starts playing a file
        addon = xbmcaddon.Addon(id='service.nextup.notification')
        self.postplaywindow = None
        WINDOW = xbmcgui.Window(10000)
        WINDOW.clearProperty("NextUpNotification.NowPlaying.DBID")
        WINDOW.clearProperty("NextUpNotification.NowPlaying.Type")
        WINDOW.clearProperty("NextUpNotification.Unskipped")
        # Get the active player
        result = self.library.get_now_playing()
        if 'result' in result:
            itemtype = result["result"]["item"]["type"]
            if itemtype == "episode":
                itemtitle = result["result"]["item"]["showtitle"].encode('utf-8')
                itemtitle = Utils.unicodetoascii(itemtitle)
                WINDOW.setProperty("NextUpNotification.NowPlaying.Type", itemtype)
                tvshowid = result["result"]["item"]["tvshowid"]
                WINDOW.setProperty("NextUpNotification.NowPlaying.DBID", str(tvshowid))
                if int(tvshowid) == -1:
                    tvshowid = self.library.showtitle_to_id(title=itemtitle)
                    self.logMsg("Fetched missing tvshowid " + str(tvshowid), 2)
                    WINDOW.setProperty("NextUpNotification.NowPlaying.DBID", str(tvshowid))

                if (addon.getSetting("enableNextUpSkip") == "true"):
                    episode = result["result"]["item"]["episode"]
                    season = result["result"]["item"]["season"]
                    if isinstance(itemtitle, unicode):
                        itemtitle = itemtitle.encode('utf-8')
                    userdata = {"title": itemtitle, "season": season, "episode": episode}
                    urllib.urlencode(userdata)
                    resp = requests.get(self.url, params=userdata, verify=False)
                    respdec = json.loads(resp.text)
                    introStart = int(respdec["start"])
                    introLength = int(respdec["length"])
                    WINDOW.setProperty("NextUpNotification.introStart", str(introStart))
                    WINDOW.setProperty("NextUpNotification.introLength", str(introLength))
                    if (addon.getSetting("enableSkipCheckDelay") == "true"):
                        self.logMsg("Using delayed setting Unskipped", 1)
                        # let's give kodi the chance to set xbmc.Player().getTime() to prevent
                        # from popup notify directly after playback starts (possible only happens on slower systems like rpi
                        time.sleep(3)

                    if ((introStart != '') or (introLength != '')):
                        WINDOW.setProperty("NextUpNotification.Unskipped", "True")
                        # it was only for debugging
                        # dlg = xbmcgui.Dialog()
                        # dlg.notification("Nextup Service Notification", 'Skipping Intro Prepared!', xbmcgui.NOTIFICATION_INFO, 2000)

            elif itemtype == "movie":
                WINDOW.setProperty("NextUpNotification.NowPlaying.Type", itemtype)
                id = result["result"]["item"]["id"]
                WINDOW.setProperty("NextUpNotification.NowPlaying.DBID", str(id))

    def onPlayBackEnded(self):
        self.logMsg("playback ended ", 2)
        if self.postplaywindow is not None:
            self.showPostPlay()

    def findNextEpisode(self, result, currentFile, includeWatched):
        self.logMsg("Find next episode called", 1)
        position = 0
        for episode in result["result"]["episodes"]:
            # find position of current episode
            if self.currentepisodeid == episode["episodeid"]:
                # found a match so add 1 for the next and get out of here
                position += 1
                break
            position += 1
        # check if it may be a multi-part episode
        while result["result"]["episodes"][position]["file"] == currentFile:
            position += 1
        # skip already watched episodes?
        while not includeWatched and result["result"]["episodes"][position]["playcount"] > 1:
            position += 1

        # now return the episode
        self.logMsg("Find next episode found next episode in position: " + str(position), 1)
        try:
            episode = result["result"]["episodes"][position]
        except:
            # no next episode found
            episode = None

        return episode

    def findCurrentEpisode(self, result, currentFile):
        self.logMsg("Find current episode called", 1)
        position = 0
        for episode in result["result"]["episodes"]:
            # find position of current episode
            if self.currentepisodeid == episode["episodeid"]:
                # found a match so get out of here
                break
            position += 1

        # now return the episode
        self.logMsg("Find current episode found episode in position: " + str(position), 1)
        try:
            episode = result["result"]["episodes"][position]
        except:
            # no next episode found
            episode = None

        return episode

    def displayRandomUnwatched(self):
        # Get the active player
        result = self.library.get_now_playing()
        if 'result' in result:
            itemtype = result["result"]["item"]["type"]
            if itemtype == "episode":
                # playing an episode so find a random unwatched show from the same genre
                genres = result["result"]["item"]["genre"]
                if genres:
                    genretitle = genres[0]
                    self.logMsg("Looking up tvshow for genre " + genretitle, 2)
                    tvshow = Utils.get_json('VideoLibrary.GetTVShows',
                                            '{ "sort": { "order": "descending", "method": "random" }, "filter": {"and": [{"operator":"is", "field":"genre", "value":"%s"}, {"operator":"is", "field":"playcount", "value":"0"}]}, "properties": [ %s ],"limits":{"end":1} }' % (
                                            genretitle, self.fields_tvshows))
                if not tvshow:
                    self.logMsg("Looking up tvshow without genre", 2)
                    tvshow = Utils.get_json('VideoLibrary.GetTVShows',
                                            '{ "sort": { "order": "descending", "method": "random" }, "filter": {"and": [{"operator":"is", "field":"playcount", "value":"0"}]}, "properties": [ %s ],"limits":{"end":1} }' % self.fields_tvshows)
                self.logMsg("Got tvshow" + str(tvshow), 2)
                tvshowid = tvshow[0]["tvshowid"]
                if int(tvshowid) == -1:
                    tvshowid = self.library.showtitle_to_id(title=itemtitle)
                    self.logMsg("Fetched missing tvshowid " + str(tvshowid), 2)
                episode = Utils.get_json('VideoLibrary.GetEpisodes',
                                         '{ "tvshowid": %d, "sort": {"method":"episode"}, "filter": {"and": [ {"field": "playcount", "operator": "lessthan", "value":"1"}, {"field": "season", "operator": "greaterthan", "value": "0"} ]}, "properties": [ %s ], "limits":{"end":1}}' % (
                                         tvshowid, self.fields_episodes))

                if episode:
                    self.logMsg("Got details of next up episode %s" % str(episode), 2)
                    addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                    unwatchedPage = UnwatchedInfo("script-nextup-notification-UnwatchedInfo.xml",
                                                  addonSettings.getAddonInfo('path'), "default", "1080i")
                    unwatchedPage.setItem(episode[0])
                    self.logMsg("Calling display unwatched", 2)
                    unwatchedPage.show()
                    monitor = xbmc.Monitor()
                    monitor.waitForAbort(10)
                    self.logMsg("Calling close unwatched", 2)
                    unwatchedPage.close()
                    del monitor

    def postPlayPlayback(self):
        currentFile = xbmc.Player().getPlayingFile()

        # Get the active player
        result = self.library.get_now_playing()
        if 'result' in result:
            itemtype = result["result"]["item"]["type"]
            addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
            playMode = addonSettings.getSetting("autoPlayMode")
            currentepisodenumber = result["result"]["item"]["episode"]
            currentseasonid = result["result"]["item"]["season"]
            currentshowtitle = result["result"]["item"]["showtitle"].encode('utf-8')
            currentshowtitle = Utils.unicodetoascii(currentshowtitle)
            tvshowid = result["result"]["item"]["tvshowid"]
            shortplayMode = addonSettings.getSetting("shortPlayMode")
            shortplayNotification = addonSettings.getSetting("shortPlayNotification")
            shortplayLength = int(addonSettings.getSetting("shortPlayLength")) * 60

        # Try to get tvshowid by showtitle from kodidb if tvshowid is -1 like in strm streams which are added to kodi db
        if int(tvshowid) == -1:
            tvshowid = self.library.showtitle_to_id(title=currentshowtitle)
            self.logMsg("Fetched missing tvshowid " + str(tvshowid), 2)

        if (itemtype == "episode"):
            # Get current episodeid
            currentepisodeid = self.library.get_episode_id(showid=str(tvshowid), showseason=currentseasonid,
                                                   showepisode=currentepisodenumber)
        else:
            # wtf am i doing here error.. ####
            self.logMsg("Error: cannot determine if episode", 1)
            return

        self.currentepisodeid = currentepisodeid
        self.logMsg("Getting details of next up episode for tvshow id: " + str(tvshowid), 1)
        if self.currenttvshowid != tvshowid:
            self.currenttvshowid = tvshowid
            self.playedinarow = 1

        result = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, '
            '"properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", '
            '"file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", '
            '"dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}'
            % tvshowid)

        if result:
            result = unicode(result, 'utf-8', errors='ignore')
            result = json.loads(result)
            self.logMsg("Got details of next up episode %s" % str(result), 2)
            xbmc.sleep(100)

            # Find the next unwatched and the newest added episodes
            if "result" in result and "episodes" in result["result"]:
                includeWatched = addonSettings.getSetting("includeWatched") == "true"
                episode = self.findNextEpisode(result, currentFile, includeWatched)
                current_episode = self.findCurrentEpisode(result, currentFile)
                self.logMsg("episode details %s" % str(episode), 2)
                episodeid = episode["episodeid"]

                if current_episode:
                    # we have something to show
                    postPlayPage = PostPlayInfo("script-nextup-notification-PostPlayInfo.xml",
                                                addonSettings.getAddonInfo('path'), "default", "1080i")
                    postPlayPage.setItem(episode)
                    postPlayPage.setPreviousItem(current_episode)
                    upnextitems = self.library.parse_tvshows_recommended(6)
                    postPlayPage.setUpNextList(upnextitems)
                    playedinarownumber = addonSettings.getSetting("playedInARow")
                    playTime = xbmc.Player().getTime()
                    totalTime = xbmc.Player().getTotalTime()
                    self.logMsg("played in a row settings %s" % str(playedinarownumber), 2)
                    self.logMsg("played in a row %s" % str(self.playedinarow), 2)
                    if int(self.playedinarow) <= int(playedinarownumber):
                        if (shortplayNotification == "false") and (shortplayLength >= totalTime) and (
                            shortplayMode == "true"):
                            self.logMsg("hiding notification for short videos")
                        else:
                            postPlayPage.setStillWatching(False)
                    else:
                        if (shortplayNotification == "false") and (shortplayLength >= totalTime) and (
                            shortplayMode == "true"):
                            self.logMsg("hiding notification for short videos")
                        else:
                            postPlayPage.setStillWatching(True)

                    self.postplaywindow = postPlayPage

    def showPostPlay(self):
        self.logMsg("showing postplay window")
        p = self.postplaywindow.doModal()
        autoplayed = xbmcgui.Window(10000).getProperty("NextUpNotification.AutoPlayed")
        self.logMsg("showing postplay window completed autoplayed? " + str(autoplayed))
        if autoplayed:
            self.playedinarow += 1
        else:
            self.playedinarow = 1
        del p

    def autoPlayPlayback(self):
        currentFile = xbmc.Player().getPlayingFile()

        # Get the active player
        result = self.library.get_now_playing()
        if 'result' in result:
            itemtype = result["result"]["item"]["type"]
            addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
            playMode = addonSettings.getSetting("autoPlayMode")
            currentepisodenumber = result["result"]["item"]["episode"]
            currentseasonid = result["result"]["item"]["season"]
            currentshowtitle = result["result"]["item"]["showtitle"].encode('utf-8')
            currentshowtitle = Utils.unicodetoascii(currentshowtitle)
            tvshowid = result["result"]["item"]["tvshowid"]
            shortplayMode = addonSettings.getSetting("shortPlayMode")
            shortplayNotification = addonSettings.getSetting("shortPlayNotification")
            shortplayLength = int(addonSettings.getSetting("shortPlayLength")) * 60
            showpostplaypreview = addonSettings.getSetting("showPostPlayPreview") == "true"
            showpostplay = addonSettings.getSetting("showPostPlay") == "true"
            shouldshowpostplay = showpostplay and showpostplaypreview

            # Try to get tvshowid by showtitle from kodidb if tvshowid is -1 like in strm streams which are added to kodi db
            if int(tvshowid) == -1:
                tvshowid = self.library.showtitle_to_id(title=currentshowtitle)
                self.logMsg("Fetched missing tvshowid " + str(tvshowid), 2)

            if (itemtype == "episode"):
                # Get current episodeid
                currentepisodeid = self.library.get_episode_id(showid=str(tvshowid), showseason=currentseasonid,
                                                       showepisode=currentepisodenumber)
            else:
                # wtf am i doing here error.. ####
                self.logMsg("Error: cannot determine if episode", 1)
                return

        else:
            # wtf am i doing here error.. ####
            self.logMsg("Error: cannot determine if episode", 1)
            return

        self.currentepisodeid = currentepisodeid
        self.logMsg("Getting details of next up episode for tvshow id: " + str(tvshowid), 1)
        if self.currenttvshowid != tvshowid:
            self.currenttvshowid = tvshowid
            self.playedinarow = 1

        result = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, '
            '"properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", '
            '"file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", '
            '"dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}'
            % tvshowid)

        if result:
            result = unicode(result, 'utf-8', errors='ignore')
            result = json.loads(result)
            self.logMsg("Got details of next up episode %s" % str(result), 2)
            xbmc.sleep(100)

            # Find the next unwatched and the newest added episodes
            if "result" in result and "episodes" in result["result"]:
                includeWatched = addonSettings.getSetting("includeWatched") == "true"
                episode = self.findNextEpisode(result, currentFile, includeWatched)

                if episode is None:
                    # no episode get out of here
                    return
                self.logMsg("episode details %s" % str(episode), 2)
                episodeid = episode["episodeid"]

                if includeWatched:
                    includePlaycount = True
                else:
                    includePlaycount = episode["playcount"] == 0
                if includePlaycount and currentepisodeid != episodeid:
                    # we have a next up episode
                    nextUpPage = NextUpInfo("script-nextup-notification-NextUpInfo.xml",
                                            addonSettings.getAddonInfo('path'), "default", "1080i")
                    nextUpPage.setItem(episode)
                    stillWatchingPage = StillWatchingInfo(
                        "script-nextup-notification-StillWatchingInfo.xml",
                        addonSettings.getAddonInfo('path'), "default", "1080i")
                    stillWatchingPage.setItem(episode)
                    playedinarownumber = addonSettings.getSetting("playedInARow")
                    playTime = xbmc.Player().getTime()
                    totalTime = xbmc.Player().getTotalTime()
                    self.logMsg("played in a row settings %s" % str(playedinarownumber), 2)
                    self.logMsg("played in a row %s" % str(self.playedinarow), 2)

                    if int(self.playedinarow) <= int(playedinarownumber):
                        self.logMsg(
                            "showing next up page as played in a row is %s" % str(self.playedinarow), 2)
                        if (shortplayNotification == "false") and (shortplayLength >= totalTime) and (
                            shortplayMode == "true"):
                            self.logMsg("hiding notification for short videos")
                        else:
                            nextUpPage.show()
                    else:
                        self.logMsg(
                            "showing still watching page as played in a row %s" % str(self.playedinarow), 2)
                        if (shortplayNotification == "false") and (shortplayLength >= totalTime) and (
                            shortplayMode == "true"):
                            self.logMsg("hiding notification for short videos")
                        else:
                            stillWatchingPage.show()
                    if shouldshowpostplay:
                        self.postPlayPlayback()

                    while xbmc.Player().isPlaying() and (
                                    totalTime - playTime > 1) and not nextUpPage.isCancel() and not nextUpPage.isWatchNow() and not stillWatchingPage.isStillWatching() and not stillWatchingPage.isCancel():
                        xbmc.sleep(100)
                        try:
                            playTime = xbmc.Player().getTime()
                            totalTime = xbmc.Player().getTotalTime()
                        except:
                            pass
                    if shortplayLength >= totalTime and shortplayMode == "true":
                        # play short video and don't add to playcount
                        self.playedinarow += 0
                        self.logMsg("Continuing short video autoplay - %s")
                        if nextUpPage.isWatchNow() or stillWatchingPage.isStillWatching():
                            self.playedinarow = 1
                        shouldPlayDefault = not nextUpPage.isCancel()
                    else:
                        if int(self.playedinarow) <= int(playedinarownumber):
                            nextUpPage.close()
                            shouldPlayDefault = not nextUpPage.isCancel()
                            shouldPlayNonDefault = nextUpPage.isWatchNow()
                        else:
                            stillWatchingPage.close()
                            shouldPlayDefault = stillWatchingPage.isStillWatching()
                            shouldPlayNonDefault = stillWatchingPage.isStillWatching()

                        if nextUpPage.isWatchNow() or stillWatchingPage.isStillWatching():
                            self.playedinarow = 1
                        else:
                            self.playedinarow += 1

                    if (shouldPlayDefault and not shouldshowpostplay and playMode == "0") or (
                            shouldPlayNonDefault and shouldshowpostplay and playMode == "0") or (
                        shouldPlayNonDefault and playMode == "1"):
                        self.logMsg("playing media episode id %s" % str(episodeid), 2)
                        # Signal to trakt previous episode watched
                        AddonSignals.sendSignal("NEXTUPWATCHEDSIGNAL", {'episodeid': self.currentepisodeid})

                        # if in postplaypreview mode clear the post play window as its not needed now
                        if shouldshowpostplay:
                            self.postplaywindow = None

                        # Play media
                        xbmc.executeJSONRPC(
                            '{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", '
                            '"params": { "item": {"episodeid": ' + str(episode["episodeid"]) + '} } }')
