import xbmcaddon
import xbmc
import xbmcgui
import os
import time

cwd = xbmcaddon.Addon(id='service.nextup.notification').getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(cwd, 'resources', 'lib'))
sys.path.append(BASE_RESOURCE_PATH)

import Utils as utils
from Player import Player
from ClientInformation import ClientInformation

class Service():
    clientInfo = ClientInformation()
    addonName = clientInfo.getAddonName()
    WINDOW = xbmcgui.Window(10000)
    lastMetricPing = time.time()

    def __init__(self, *args):
        addonName = self.addonName

        self.logMsg("Starting NextUp Service", 0)
        self.logMsg("========  START %s  ========" % addonName, 0)
        self.logMsg("KODI Version: %s" % xbmc.getInfoLabel("System.BuildVersion"), 0)
        self.logMsg("%s Version: %s" % (addonName, self.clientInfo.getVersion()), 0)

    def logMsg(self, msg, lvl=1):
        className = self.__class__.__name__
        utils.logMsg("%s %s" % (self.addonName, className), str(msg), int(lvl))

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
            self.logMsg("Getting details of now  playing media for skip intro", 1)
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str(
                    playerid) + ', "properties": ["showtitle", "season"] } }')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got details of now playing media for skip intro" + result, 2)

            result = json.loads(result)
            return result

    def ServiceEntryPoint(self):
        player = Player()
        monitor = xbmc.Monitor()
        lastFile = None
        lastUnwatchedFile = None

        while not monitor.abortRequested():
            # check every 5 sec
            if monitor.waitForAbort(5):
                # Abort was requested while waiting. We should exit
                break
            if xbmc.Player().isPlaying():
                try:
                    playTime = xbmc.Player().getTime()

                    totalTime = xbmc.Player().getTotalTime()

                    currentFile = xbmc.Player().getPlayingFile()

                    addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                    notificationtime = addonSettings.getSetting("autoPlaySeasonTime")
                    nextUpDisabled = addonSettings.getSetting("disableNextUp") == "true"
                    nextUpSkipEnabled = addonSettings.getSetting("enableNextUpSkip") == "true"
                    nextUpSkipEnabled3rdP = addonSettings.getSetting("enableNextUpSkip3rdP") == "true"
                    nextUpSkipEnabledNoPause = addonSettings.getSetting("enableNextUpSkipNoPause") == "true"
                    randomunwatchedtime = addonSettings.getSetting("displayRandomUnwatchedTime")
                    displayrandomunwatched = addonSettings.getSetting("displayRandomUnwatched") == "true"
                    showpostplay = addonSettings.getSetting("showPostPlay") == "true"
                    showpostplaypreview = addonSettings.getSetting("showPostPlayPreview") == "true"

                    if xbmcgui.Window(10000).getProperty("NextUpNotification.Unskipped") == "True" and (nextUpSkipEnabled or nextUpSkipEnabled3rdP):
                        introStart = int(xbmcgui.Window(10000).getProperty("NextUpNotification.introStart"))
                        introLenght = int(xbmcgui.Window(10000).getProperty("NextUpNotification.introLenght"))
                        if ((playTime >= introStart) and (playTime < (playTime+introLenght))):
                            dlg = xbmcgui.Dialog()
                            dlg.notification("Nextup Service Notification", 'Skipping Intro...', xbmcgui.NOTIFICATION_INFO, 5000)
			    if nextUpSkipEnabledNoPause == "true":
				xbmc.Player().seekTime(introStart+introLenght)
				xbmcgui.Window(10000).clearProperty("NextUpNotification.Unskipped")
			    else:
				xbmc.Player().pause()
				time.sleep(1) # give kodi the chance to execute
				xbmc.Player().seekTime(introStart+introLenght)
				time.sleep(1) # give kodi the chance to execute
				xbmc.Player().pause()# unpause playback at seek position
				xbmcgui.Window(10000).clearProperty("NextUpNotification.Unskipped")

                    if xbmcgui.Window(10000).getProperty("PseudoTVRunning") != "True" and not nextUpDisabled:

                        if (not showpostplay or (showpostplaypreview and showpostplay)) and (totalTime - playTime <= int(notificationtime) and (
                                        lastFile is None or lastFile != currentFile)) and totalTime != 0:
                            lastFile = currentFile
                            self.logMsg("Calling autoplayback totaltime - playtime is %s" % (totalTime - playTime), 2)
                            player.autoPlayPlayback()
                            self.logMsg("Netflix style autoplay succeeded.", 2)

                        if (showpostplay and not showpostplaypreview) and (totalTime - playTime <= 10) and totalTime != 0:
                            self.logMsg("Calling post playback", 2)
                            player.postPlayPlayback()

                        if displayrandomunwatched and (int(playTime) >= int(randomunwatchedtime)) and (int(playTime) < int(int(randomunwatchedtime)+100)) and (
                                        lastUnwatchedFile is None or lastUnwatchedFile != currentFile):
                            self.logMsg("randomunwatchedtime is %s" % (int(randomunwatchedtime)), 2)
                            self.logMsg("Calling display unwatched", 2)
                            lastUnwatchedFile = currentFile
                            player.displayRandomUnwatched()

                except Exception as e:
                    self.logMsg("Exception in Playback Monitor Service: %s" % e)

        self.logMsg("======== STOP %s ========" % self.addonName, 0)

# start the service
Service().ServiceEntryPoint()
