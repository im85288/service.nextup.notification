import xbmcaddon
import xbmc
import xbmcgui
import Utils as utils
import AddonSignals
import library
from ClientInformation import ClientInformation
from NextUpInfo import NextUpInfo
from StillWatchingInfo import StillWatchingInfo
from UnwatchedInfo import UnwatchedInfo
from PostPlayInfo import PostPlayInfo
import sys

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json
LIBRARY = library.LibraryFunctions()
# service class for playback monitoring


class Player(xbmc.Player):
    # Borg - multiple instances, shared state
    _shared_state = {}

    xbmcplayer = xbmc.Player()
    clientInfo = ClientInformation()

    addonName = clientInfo.getAddonName()
    addonId = clientInfo.getAddonId()
    addon = xbmcaddon.Addon(id=addonId)

    logLevel = 0
    currenttvshowid = None
    currentepisodeid = None
    playedinarow = 1
    fields_base = '"dateadded", "file", "lastplayed","plot", "title", "art", "playcount",'
    fields_file = fields_base + '"streamdetails", "director", "resume", "runtime",'
    fields_tvshows = fields_base + '"sorttitle", "mpaa", "premiered", "year", "episode", "watchedepisodes", "votes", "rating", "studio", "season", "genre", "episodeguide", "tag", "originaltitle", "imdbnumber"'
    fields_episodes = fields_file + '"cast", "productioncode", "rating", "votes", "episode", "showtitle", "tvshowid", "season", "firstaired", "writer", "originaltitle"'
    postplaywindow = None

    def __init__(self, *args):
        self.__dict__ = self._shared_state
        self.logMsg("Starting playback monitor service", 1)
        self.emby_data = None
        self.emby_mode = False
        self.addon_settings = xbmcaddon.Addon(id='service.nextup.notification')
        AddonSignals.registerSlot('embycon', 'embycon_next_episode', self.emby_data_received)

    def logMsg(self, msg, lvl=1):
        self.className = self.__class__.__name__
        utils.logMsg("%s %s" % (self.addonName, self.className), msg, int(lvl))

    def parse_tvshows_recommended(self, limit):
        items = []
        prefix = "recommended-episodes"
        json_query = LIBRARY._fetch_recommended_episodes()

        if json_query:
            # First unplayed episode of recent played tvshows
            self.logMsg("getting next up tvshows " + json_query, 2)
            json_query = json.loads(json_query)
            if "result" in json_query and 'tvshows' in json_query['result']:
                count = -1
                for item in json_query['result']['tvshows']:
                    if xbmc.abortRequested:
                        break
                    if count == -1:
                        count += 1
                        continue
                    json_query2 = xbmcgui.Window(10000).getProperty(prefix + "-data-" + str(item['tvshowid']))
                    if json_query2:
                        self.logMsg("getting next up episodes " + json_query2, 2)
                        json_query2 = json.loads(json_query2)
                        if "result" in json_query2 and json_query2['result'] is not None and 'episodes' in json_query2['result']:
                            for item2 in json_query2['result']['episodes']:
                                episode = "%.2d" % float(item2['episode'])
                                season = "%.2d" % float(item2['season'])
                                episodeno = "s%se%s" % (season, episode)
                                break
                            plot = item2['plot']
                            episodeid = str(item2['episodeid'])
                            if len(item['studio']) > 0:
                                studio = item['studio'][0]
                            else:
                                studio = ""
                            if "director" in item2:
                                director = " / ".join(item2['director'])
                            if "writer" in item2:
                                writer = " / ".join(item2['writer'])

                            liz = xbmcgui.ListItem(item2['title'])
                            liz.setPath(item2['file'])
                            liz.setProperty('IsPlayable', 'true')
                            liz.setInfo(type="Video", infoLabels={"Title": item2['title'],
                                                                  "Episode": item2['episode'],
                                                                  "Season": item2['season'],
                                                                  "Studio": studio,
                                                                  "Premiered": item2['firstaired'],
                                                                  "Plot": plot,
                                                                  "TVshowTitle": item2['showtitle'],
                                                                  "Rating": str(float(item2['rating'])),
                                                                  "MPAA": item['mpaa'],
                                                                  "Playcount": item2['playcount'],
                                                                  "Director": director,
                                                                  "Writer": writer,
                                                                  "mediatype": "episode"})
                            liz.setProperty("episodeid",episodeid)
                            liz.setProperty("episodeno", episodeno)
                            liz.setProperty("resumetime", str(item2['resume']['position']))
                            liz.setProperty("totaltime", str(item2['resume']['total']))
                            liz.setProperty("type",'episode')
                            liz.setProperty("fanart_image", item2['art'].get('tvshow.fanart', ''))
                            liz.setProperty("dbid", str(item2['episodeid']))
                            liz.setArt(item2['art'])
                            liz.setThumbnailImage(item2['art'].get('thumb', ''))
                            liz.setIconImage('DefaultTVShows.png')
                            hasVideo = False
                            for key, value in item2['streamdetails'].iteritems():
                                for stream in value:
                                    if 'video' in key:
                                        hasVideo = True
                                    liz.addStreamInfo(key, stream)

                            # if duration wasnt in the streaminfo try adding the scraped one
                            if not hasVideo:
                                stream = {'duration': item2['runtime']}
                                liz.addStreamInfo("video", stream)

                            items.append(liz)

                            count += 1
                            if count == limit:
                                break
                    if count == limit:
                        break
            del json_query
        self.logMsg("getting next up episodes completed ", 2)
        return items

    def json_query(self, query, ret):
        try:
            xbmc_request = json.dumps(query)
            result = xbmc.executeJSONRPC(xbmc_request)
            result = unicode(result, 'utf-8', errors='ignore')
            if ret:
                return json.loads(result)['result']

            else:
                return json.loads(result)
        except:
            xbmc_request = json.dumps(query)
            result = xbmc.executeJSONRPC(xbmc_request)
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg(json.loads(result), 1)
            return json.loads(result)

    def getNowPlaying(self):
        # Get the active player
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
        result = unicode(result, 'utf-8', errors='ignore')
        self.logMsg("Got active player " + result, 2)
        result = json.loads(result)

        # Seems to work too fast loop whilst waiting for it to become active
        while not result["result"]:
            result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got active player " + result, 2)
            result = json.loads(result)

        if 'result' in result and result["result"][0] is not None:
            playerid = result["result"][0]["playerid"]

            # Get details of the playing media
            self.logMsg("Getting details of now  playing media", 1)
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str(
                    playerid) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount","genre","plotoutline"] } }')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got details of now playing media" + result, 2)

            result = json.loads(result)
            return result

    def onPlayBackStarted(self):
        # Will be called when xbmc starts playing a file
        addon = xbmcaddon.Addon(id='service.nextup.notification')
        self.postplaywindow = None
        WINDOW = xbmcgui.Window(10000)
        WINDOW.clearProperty("NextUpNotification.NowPlaying.DBID")
        WINDOW.clearProperty("NextUpNotification.NowPlaying.Type")
        # Get the active player
        result = self.getNowPlaying()
        if 'result' in result:
            itemtype = result["result"]["item"]["type"]
            if itemtype == "episode":
                itemtitle = result["result"]["item"]["showtitle"].encode('utf-8')
                itemtitle = utils.unicodetoascii(itemtitle)
                WINDOW.setProperty("NextUpNotification.NowPlaying.Type", itemtype)
                tvshowid = result["result"]["item"]["tvshowid"]
                WINDOW.setProperty("NextUpNotification.NowPlaying.DBID", str(tvshowid))
                if int(tvshowid) == -1:
                    tvshowid = self.showtitle_to_id(title=itemtitle)
                    self.logMsg("Fetched missing tvshowid " + str(tvshowid), 2)
                    WINDOW.setProperty("NextUpNotification.NowPlaying.DBID", str(tvshowid))
            elif itemtype == "movie":
                WINDOW.setProperty("NextUpNotification.NowPlaying.Type", itemtype)
                id = result["result"]["item"]["id"]
                WINDOW.setProperty("NextUpNotification.NowPlaying.DBID", str(id))

    def showtitle_to_id(self, title):
        query = {
                "jsonrpc": "2.0",
                "method": "VideoLibrary.GetTVShows",
                "params": {
                    "properties": ["title"]
                },
                "id": "libTvShows"
                }
        try:
            json_result = json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))
            if 'result' in json_result and 'tvshows' in json_result['result']:
                json_result = json_result['result']['tvshows']
                for tvshow in json_result:
                    if tvshow['label'] == title:
                        return tvshow['tvshowid']
            return '-1'
        except Exception:
            return '-1'

    def get_episode_id(self, showid, showseason, showepisode):
        showseason = int(showseason)
        showepisode = int(showepisode)
        episodeid = 0
        query = {
                "jsonrpc": "2.0",
                "method": "VideoLibrary.GetEpisodes",
                "params": {
                    "properties": ["season", "episode"],
                    "tvshowid": int(showid)
                },
                "id": "1"
                }
        try:
            json_result = json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))
            if 'result' in json_result and 'episodes' in json_result['result']:
                json_result = json_result['result']['episodes']
                for episode in json_result:
                    if episode['season'] == showseason and episode['episode'] == showepisode:
                        if 'episodeid' in episode:
                            episodeid = episode['episodeid']
            return episodeid
        except Exception:
            return episodeid

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

    def displayRandomUnwatched(self):
        # Get the active player
        result = self.getNowPlaying()
        if 'result' in result:
            itemtype = result["result"]["item"]["type"]
            if itemtype == "episode":
                # playing an episode so find a random unwatched show from the same genre
                genres = result["result"]["item"]["genre"]
                if genres:
                    genretitle = genres[0]
                    self.logMsg("Looking up tvshow for genre " + genretitle, 2)
                    tvshow = utils.getJSON('VideoLibrary.GetTVShows', '{ "sort": { "order": "descending", "method": "random" }, "filter": {"and": [{"operator":"is", "field":"genre", "value":"%s"}, {"operator":"is", "field":"playcount", "value":"0"}]}, "properties": [ %s ],"limits":{"end":1} }' % (genretitle, self.fields_tvshows))
                if not tvshow:
                    self.logMsg("Looking up tvshow without genre", 2)
                    tvshow = utils.getJSON('VideoLibrary.GetTVShows', '{ "sort": { "order": "descending", "method": "random" }, "filter": {"and": [{"operator":"is", "field":"playcount", "value":"0"}]}, "properties": [ %s ],"limits":{"end":1} }' % self.fields_tvshows)
                self.logMsg("Got tvshow" + str(tvshow), 2)
                tvshowid = tvshow[0]["tvshowid"]
                episode = utils.getJSON('VideoLibrary.GetEpisodes', '{ "tvshowid": %d, "sort": {"method":"episode"}, "filter": {"and": [ {"field": "playcount", "operator": "lessthan", "value":"1"}, {"field": "season", "operator": "greaterthan", "value": "0"} ]}, "properties": [ %s ], "limits":{"end":1}}' % (tvshowid, self.fields_episodes))

                if episode:
                    self.logMsg("Got details of next up episode %s" % str(episode), 2)
                    unwatchedPage = UnwatchedInfo("script-nextup-notification-UnwatchedInfo.xml",
                    self.addon_settings.getAddonInfo('path'), "default", "1080i")
                    unwatchedPage.setItem(episode[0])
                    self.logMsg("Calling display unwatched", 2)
                    unwatchedPage.show()
                    monitor = xbmc.Monitor()
                    monitor.waitForAbort(10)
                    self.logMsg("Calling close unwatched", 2)
                    unwatchedPage.close()
                    del monitor

    def postPlayPlayback(self):
        self.emby_mode = False
        currentFile = xbmc.Player().getPlayingFile()
        # Get the active player
        result = self.getNowPlaying()
        if not self.handle_now_playing_result(result):
            self.logMsg("Error: no result returned from check on now playing...exiting", 1)
            return

        if not self.emby_mode:
            # get the next episode from kodi
            episode = self.hanled_kodi_lookup_of_episode(self.tvshowid, currentFile, self.includeWatched)
            current_episode = self.handle_kodi_lookup_of_current_episode(self.tvshowid)
        else:
            episode = self.transform_emby_data_to_kodi_format(self.handle_emby_lookup_of_episode(self.embyid))
            current_episode = self.transform_emby_data_to_kodi_format(self.handle_emby_lookup_of_current_episode(self.embyid))

        if episode is None:
            # no episode get out of here
            self.logMsg("Error: no episode could be found to play next...exiting", 1)
            return

        self.logMsg("episode details %s" % str(episode), 2)
        if current_episode:
            # we have something to show
            postPlayPage = PostPlayInfo("script-nextup-notification-PostPlayInfo.xml",
                                        self.addon_settings.getAddonInfo('path'), "default", "1080i")
            postPlayPage.setItem(episode)
            postPlayPage.setPreviousItem(current_episode)
            if not self.emby_mode:
                upnextitems = self.parse_tvshows_recommended(6)
            else:
                # todo get emby next up items
                upnextitems = None
            postPlayPage.setUpNextList(upnextitems)
            postPlayPage.setEmbyMode(self.emby_mode)
            playedinarownumber = self.addon_settings.getSetting("playedInARow")
            totalTime = xbmc.Player().getTotalTime()
            self.logMsg("played in a row settings %s" % str(playedinarownumber), 2)
            self.logMsg("played in a row %s" % str(self.playedinarow), 2)
            if int(self.playedinarow) <= int(playedinarownumber):
                if (self.shortplayNotification == "false") and (self.shortplayLength >= totalTime) and (self.shortplayMode == "true"):
                    self.logMsg("hiding notification for short videos")
                else:
                    postPlayPage.setStillWatching(False)
            else:
                if (self.shortplayNotification == "false") and (self.shortplayLength >= totalTime) and (self.shortplayMode == "true"):
                    self.logMsg("hiding notification for short videos")
                else:
                    postPlayPage.setStillWatching(True)

            self.postplaywindow = postPlayPage

    def showPostPlay(self):
        self.logMsg("showing postplay window")
        p = self.postplaywindow.doModal()
        autoplayed = xbmcgui.Window(10000).getProperty("NextUpNotification.AutoPlayed")
        self.logMsg("showing postplay window completed autoplayed? "+str(autoplayed))
        if autoplayed:
            self.playedinarow += 1
        else:
            self.playedinarow = 1
        del p

    def handle_kodi_lookup_of_episode(self, tvshowid, currentFile, includeWatched):
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
                episode = self.findNextEpisode(result, currentFile, includeWatched)
                return episode

    def handle_kodi_lookup_of_current_episode(self, tvshowid):
        result = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, '
            '"properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", '
            '"file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", '
            '"dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}'
            % tvshowid)
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

    def handle_emby_lookup_of_episode(self, embyid):
        self.logMsg("handle_emby_lookup_of_episode called with embyid %s " % str(embyid), 2)
        if self.emby_data:
            previousembyid = self.emby_data["current_item"]["id"]
            if str(previousembyid) == str(embyid):
                self.logMsg("handle_emby_lookup_of_episode returning data %s " % str(self.emby_data["next_item"]), 2)
                return self.emby_data["next_item"]

    def handle_emby_lookup_of_current_episode(self, embyid):
        self.logMsg("handle_emby_lookup_of_current_episode called with embyid %s " % str(embyid), 2)
        if self.emby_data:
            previousembyid = self.emby_data["current_item"]["id"]
            if str(previousembyid) == embyid:
                return self.emby_data["current_item"]

    def emby_data_received(self, data):
        self.logMsg("emby_data_received called with data %s " % str(data), 2)
        self.emby_data = data

    def transform_emby_data_to_kodi_format(self, episode):
        self.logMsg("transform_emby_data_to_kodi_format called with data %s " % str(episode), 2)
        data = {}
        data["episodeid"] = episode["id"]
        data["art"] = {}
        data["art"]["tvshow.poster"] = episode["image"]
        data["art"]["thumb"] = episode["thumb"]
        data["art"]["tvshow.fanart"] = episode["fanartimage"]
        data["plot"] = episode["overview"]
        data["showtitle"] = episode["tvshowtitle"]
        data["title"] = episode["title"]
        data["playcount"] = episode["playcount"]
        data["season"] = episode["season"]
        data["episode"] = episode["episode"]
        data["rating"] = episode["rating"]
        data["firstaired"] = episode["year"]
        self.logMsg("transform_emby_data_to_kodi_format completed with data %s " % str(data), 2)
        return data

    def handle_now_playing_result(self, result):
        if 'result' in result:
            itemtype = result["result"]["item"]["type"]
            self.addon_settings = xbmcaddon.Addon(id='service.nextup.notification')
            self.playMode = self.addon_settings.getSetting("autoPlayMode")
            self.currentepisodenumber = result["result"]["item"]["episode"]
            self.currentseasonid = result["result"]["item"]["season"]
            self.currentshowtitle = result["result"]["item"]["showtitle"].encode('utf-8')
            self.currentshowtitle = utils.unicodetoascii( self.currentshowtitle)
            self.tvshowid = result["result"]["item"]["tvshowid"]
            self.embyid = result["result"]["item"]["plotoutline"]
            self.shortplayMode = self.addon_settings.getSetting("shortPlayMode")
            self.shortplayNotification= self.addon_settings.getSetting("shortPlayNotification")
            self.shortplayLength = int(self.addon_settings.getSetting("shortPlayLength")) * 60
            self.showpostplaypreview = self.addon_settings.getSetting("showPostPlayPreview") == "true"
            self.showpostplay = self.addon_settings.getSetting("showPostPlay") == "true"
            self.shouldshowpostplay =  self.showpostplay and  self.showpostplaypreview
            self.includeWatched = self.addon_settings.getSetting("includeWatched") == "true"
            if itemtype == "episode":
                if self.embyid:
                    embyid = str(self.embyid)
                    if embyid.startswith("emby_id:"):
                        self.embyid = embyid[8:]
                        self.logMsg("EmbyID retrieved %s " % str(embyid), 2)
                        self.emby_mode = True
                        currentepisodeid = embyid
                else:
                    embyid = ""

                if not embyid:
                    # Try to get tvshowid by showtitle from kodidb if tvshowid is -1 like in strm streams which are added to kodi db
                    if int(self.tvshowid) == -1:
                        self.tvshowid = self.showtitle_to_id(title=self.currentshowtitle)
                        self.logMsg("Fetched missing tvshowid " + str( self.tvshowid), 2)

                    # Get current episodeid
                    currentepisodeid = self.get_episode_id(showid=str(self.tvshowid), showseason=self.currentseasonid, showepisode=self.currentepisodenumber)
            else:
                # wtf am i doing here error.. ####
                self.logMsg("Error: cannot determine if episode", 1)
                return False
        else:
            # wtf am i doing here error.. ####
            self.logMsg("Error: no result returned from check on now playing...exiting", 1)
            return False

        self.currentepisodeid = currentepisodeid
        if self.currenttvshowid != self.tvshowid:
            self.currenttvshowid = self.tvshowid
            self.playedinarow = 1

        return True

    def autoPlayPlayback(self):
        self.emby_mode = False
        currentFile = xbmc.Player().getPlayingFile()
        # Get the active player
        result = self.getNowPlaying()
        if not self.handle_now_playing_result(result):
            self.logMsg("Error: no result returned from check on now playing...exiting", 1)
            return

        if not self.emby_mode:
            # get the next episode from kodi
            episode = self.handle_kodi_lookup_of_episode(self.tvshowid, currentFile, self.includeWatched)
        else:
            episode = self.transform_emby_data_to_kodi_format(self.handle_emby_lookup_of_episode(self.embyid))

        if episode is None:
            # no episode get out of here
            self.logMsg("Error: no episode could be found to play next...exiting", 1)
            return
        self.logMsg("episode details %s" % str(episode), 2)
        episodeid = episode["episodeid"]
        includePlaycount = True if self.includeWatched else episode["playcount"] == 0
        if includePlaycount and self.currentepisodeid != episodeid:
            # we have a next up episode
            nextUpPage = NextUpInfo("script-nextup-notification-NextUpInfo.xml",
                                    self.addon_settings.getAddonInfo('path'), "default", "1080i")
            nextUpPage.setItem(episode)
            stillWatchingPage = StillWatchingInfo(
                "script-nextup-notification-StillWatchingInfo.xml",
                self.addon_settings.getAddonInfo('path'), "default", "1080i")
            stillWatchingPage.setItem(episode)
            playedinarownumber = self.addon_settings.getSetting("playedInARow")
            playTime = xbmc.Player().getTime()
            totalTime =  xbmc.Player().getTotalTime()
            self.logMsg("played in a row settings %s" % str(playedinarownumber), 2)
            self.logMsg("played in a row %s" % str(self.playedinarow), 2)

            if int(self.playedinarow) <= int(playedinarownumber):
                self.logMsg(
                    "showing next up page as played in a row is %s" % str(self.playedinarow), 2)
                if (self.shortplayNotification == "false") and (self.shortplayLength >= totalTime) and (self.shortplayMode == "true"):
                    self.logMsg("hiding notification for short videos")
                else:
                    nextUpPage.show()
            else:
                self.logMsg(
                    "showing still watching page as played in a row %s" % str(self.playedinarow), 2)
                if (self.shortplayNotification == "false") and (self.shortplayLength >= totalTime) and (self.shortplayMode == "true"):
                    self.logMsg("hiding notification for short videos")
                else:
                    stillWatchingPage.show()
            if self.shouldshowpostplay:
                self.postPlayPlayback()

            while xbmc.Player().isPlaying() and (
                    totalTime - playTime > 1) and not nextUpPage.isCancel() and not nextUpPage.isWatchNow() and not stillWatchingPage.isStillWatching() and not stillWatchingPage.isCancel():
                xbmc.sleep(100)
                try:
                    playTime = xbmc.Player().getTime()
                    totalTime = xbmc.Player().getTotalTime()
                except:
                    pass
            if self.shortplayLength >= totalTime and self.shortplayMode == "true":
                #play short video and don't add to playcount
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

            if (shouldPlayDefault and not self.shouldshowpostplay and self.playMode == "0") or (shouldPlayNonDefault and self.shouldshowpostplay and self.playMode == "0") or (shouldPlayNonDefault and self.playMode == "1"):
                self.logMsg("playing media episode id %s" % str(episodeid), 2)
                # Signal to trakt previous episode watched
                AddonSignals.sendSignal("NEXTUPWATCHEDSIGNAL", {'episodeid': self.currentepisodeid})

                # if in postplaypreview mode clear the post play window as its not needed now
                if self.shouldshowpostplay:
                    self.postplaywindow = None

                # Play media
                if not self.emby_mode:
                    xbmc.executeJSONRPC(
                        '{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", '
                        '"params": { "item": {"episodeid": ' + str(episode["episodeid"]) + '} } }')
                else:
                    self.logMsg("sending id %s to embyCon to play" % str(episodeid))
                    play_info = {'item_id': str(episodeid), 'auto_resume': False, 'force_transcode': False, 'media_source_id': '', 'use_default': True}
                    AddonSignals.sendSignal("embycon_play_action", play_info, source_id="embycon")

