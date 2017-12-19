import xbmcgui
import xbmc
import xbmcaddon
import inspect
import sys

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json
addon_settings = xbmcaddon.Addon(id='service.nextup.notification')


class CommonFunctions:
    @staticmethod
    def get_home_window():
        return xbmcgui.Window(10000)

    @staticmethod
    def log(title, msg, level=1):
        log_level = int(addon_settings.getSetting("logLevel"))
        CommonFunctions.get_home_window().setProperty('logLevel', str(log_level))
        if log_level >= level:
            if log_level == 2:  # inspect.stack() is expensive
                try:
                    xbmc.log(title + " -> " + inspect.stack()[1][3] + " : " + str(msg), level=xbmc.LOGNOTICE)
                except UnicodeEncodeError:
                    xbmc.log(title + " -> " + inspect.stack()[1][3] + " : " + str(msg.encode('utf-8')),
                             level=xbmc.LOGNOTICE)
            else:
                try:
                    xbmc.log(title + " -> " + str(msg), level=xbmc.LOGNOTICE)
                except UnicodeEncodeError:
                    xbmc.log(title + " -> " + str(msg.encode('utf-8')), level=xbmc.LOGNOTICE)


class AddonSettings:
    def getSetting(self, key):
        return addon_settings.getSetting(key)

    def getAddonInfo(self, key):
        return addon_settings.getAddonInfo(key)
