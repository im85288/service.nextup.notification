import xbmcaddon
import xbmc
import xbmcgui
import os
import time
from resources.lib.common_functions import CommonFunctions
from resources.lib.common_functions import AddonSettings
from resources.lib.client_information import ClientInformation
from resources.lib.player import Player
from resources.lib.skip_intro import SkipIntro

cwd = xbmcaddon.Addon(id='service.nextup.notification').getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(cwd, 'resources', 'lib'))
sys.path.append(BASE_RESOURCE_PATH)


class Service:
    clientInfo = ClientInformation()
    addonName = clientInfo.getAddonName()
    addon_settings = AddonSettings()

    def __init__(self):
        self.log("Starting NextUp Service", 0)
        self.log("========  START %s  ========" % self.addonName, 0)
        self.log("KODI Version: %s" % xbmc.getInfoLabel("System.BuildVersion"), 0)
        self.log("%s Version: %s" % (self.addonName, self.clientInfo.getVersion()), 0)

    def log(self, msg, lvl=1):
        CommonFunctions.log("%s %s" % (self.addonName, self.__class__.__name__), str(msg), int(lvl))

    def launch_service(self):
        home_window = CommonFunctions.get_home_window()
        player = Player()
        monitor = xbmc.Monitor()
        last_file = None
        last_unwatched_file = None

        while not monitor.abortRequested():
            # check every 1 sec
            if monitor.waitForAbort(1):
                # Abort was requested while waiting. We should exit
                break
            if xbmc.Player().isPlaying():
                try:
                    playTime = xbmc.Player().getTime()
                    totalTime = xbmc.Player().getTotalTime()
                    currentFile = xbmc.Player().getPlayingFile()
                    notificationtime = self.addon_settings.getSetting("autoPlaySeasonTime")
                    nextUpDisabled = self.addon_settings.getSetting("disableNextUp") == "true"
                    nextUpSkipEnabled = self.addon_settings.getSetting("enableNextUpSkip") == "true"
                    nextUpSkipEnabledAuto = self.addon_settings.getSetting("enableAutoSkip") == "true"
                    nextUpSkipEnabled3rdP = self.addon_settings.getSetting("enableNextUpSkip3rdP") == "true"
                    nextUpSkipEnabledNoPause = self.addon_settings.getSetting("enableNextUpSkipNoPause") == "true"
                    randomunwatchedtime = self.addon_settings.getSetting("displayRandomUnwatchedTime")
                    displayrandomunwatched = self.addon_settings.getSetting("displayRandomUnwatched") == "true"
                    showpostplay = self.addon_settings.getSetting("showPostPlay") == "true"
                    showpostplaypreview = self.addon_settings.getSetting("showPostPlayPreview") == "true"

                    if home_window.getProperty("NextUpNotification.Unskipped") == "True" and (
                        nextUpSkipEnabled or nextUpSkipEnabled3rdP):
                        introStart = int(home_window.getProperty("NextUpNotification.introStart"))
                        introLength = int(home_window.getProperty("NextUpNotification.introLength"))
                        self.log("skip intro check playtime is " + str(playTime) + " introstart is " + str(introStart),
                                 1)
                        if ((introStart == 99999) or (introLength == 0) or (introLength == 99999)):
                            self.log("Intro not set for episode (start=" + str(introStart) + " / length=" + str(
                                introLength) + ") -> disable checks for this episode", 1)
                            home_window.clearProperty("NextUpNotification.Unskipped")
                        if ((playTime >= introStart) and (playTime < (playTime + introLength))):
                            if nextUpSkipEnabledAuto == 1:
                                dlg = xbmcgui.Dialog()
                                dlg.notification("Nextup Service Notification", 'Skipping Intro...',
                                                 xbmcgui.NOTIFICATION_INFO, 5000)

                                if nextUpSkipEnabledNoPause == 1:
                                    xbmc.Player().seekTime(introStart + introLength)
                                    home_window.clearProperty("NextUpNotification.Unskipped")
                                else:
                                    xbmc.Player().pause()
                                    time.sleep(1)  # give kodi the chance to execute
                                    xbmc.Player().seekTime(introStart + introLength)
                                    time.sleep(1)  # give kodi the chance to execute
                                    xbmc.Player().pause()  # unpause playback at seek position
                                    home_window.clearProperty("NextUpNotification.Unskipped")
                            else:
                                skipIntroPage = SkipIntro("script-nextup-notification-SkipIntro.xml",
                                                          self.addon_settings.getAddonInfo('path'), "default", "1080i")
                                # close skip intro dialog after time
                                xbmc.executebuiltin('AlarmClock(closedialog,Dialog.Close(all,true),00:15,silent)')
                                self.log("showing skip intro page")
                                home_window.clearProperty("NextUpNotification.Unskipped")
                                skipIntroPage.show()

                    if home_window.getProperty("PseudoTVRunning") != "True" and not nextUpDisabled:

                        if (not showpostplay or (showpostplaypreview and showpostplay)) and (
                                    totalTime - playTime <= int(notificationtime) and (
                                        last_file is None or last_file != currentFile)) and totalTime != 0:
                            last_file = currentFile
                            self.log("Calling autoplayback totaltime - playtime is %s" % (totalTime - playTime), 2)
                            player.autoPlayPlayback()
                            self.log("Netflix style autoplay succeeded.", 2)

                        if (showpostplay and not showpostplaypreview) and (
                                totalTime - playTime <= 10) and totalTime != 0:
                            self.log("Calling post playback", 2)
                            player.postPlayPlayback()

                        if displayrandomunwatched and (int(playTime) >= int(randomunwatchedtime)) and (
                            int(playTime) < int(int(randomunwatchedtime) + 100)) and (
                                        last_unwatched_file is None or last_unwatched_file != currentFile):
                            self.log("randomunwatchedtime is %s" % (int(randomunwatchedtime)), 2)
                            self.log("Calling display unwatched", 2)
                            last_unwatched_file = currentFile
                            player.displayRandomUnwatched()

                except Exception as e:
                    self.log("Exception in Playback Monitor Service: %s" % e)

        self.log("======== STOP %s ========" % self.addonName, 0)


# start the service
Service().launch_service()
