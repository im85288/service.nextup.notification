import os
import sys

import xbmc
import xbmcaddon

from resources.lib.addon_information import AddonInformation
from resources.lib.logger import Logger
from resources.lib.playback_monitor import PlaybackMonitor

cwd = xbmcaddon.Addon(id='service.nextup.notification').getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(cwd, 'resources', 'lib'))
sys.path.append(BASE_RESOURCE_PATH)


class Service:
    def __init__(self):
        self.addon_info = AddonInformation()
        self.logger = Logger("%s %s" % (self.addon_info.get_addon_name(), self.__class__.__name__))
        self.logger.log("Starting NextUp Service", 0)
        self.logger.log("========  START %s  ========" % self.addon_info.get_addon_name(), 0)
        self.logger.log("KODI Version: %s" % xbmc.getInfoLabel("System.BuildVersion"), 0)
        self.logger.log("%s Version: %s" % (self.addon_info.get_addon_name(), self.addon_info.get_version()), 0)
        self.playback_monitor = PlaybackMonitor()
        self.monitor = xbmc.Monitor()

    def __str__(self):
        return "Service for %s" % self.addon_info.get_addon_name()

    def launch_service(self):

        while not self.monitor.abortRequested():
            # check every 1 sec
            if self.monitor.waitForAbort(1):
                # Abort was requested while waiting. We should exit
                break
            if xbmc.Player().isPlaying():
                self.playback_monitor.monitor_playback()

        self.logger.log("======== STOP %s ========" % self.addonName, 0)


# start the service
Service().launch_service()
