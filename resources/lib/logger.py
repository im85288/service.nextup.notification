import inspect

import xbmc

from addon_settings import AddonSettings
from common import Common


class Logger:
    def __init__(self, title):
        self.title = title
        self.addon_settings = AddonSettings()

    def log(self, msg, level=1):
        log_level = int(self.addon_settings.get_setting(AddonSettings.LOG_LEVEL))
        Common.get_home_window().setProperty(AddonSettings.LOG_LEVEL, str(log_level))
        if log_level >= int(level):
            if log_level == 2:  # inspect.stack() is expensive
                try:
                    xbmc.log(self.title + " -> " + inspect.stack()[1][3] + " : " + str(msg), level=xbmc.LOGNOTICE)
                except UnicodeEncodeError:
                    xbmc.log(self.title + " -> " + inspect.stack()[1][3] + " : " + str(msg.encode('utf-8')),
                             level=xbmc.LOGNOTICE)
            else:
                try:
                    xbmc.log(self.title + " -> " + str(msg), level=xbmc.LOGNOTICE)
                except UnicodeEncodeError:
                    xbmc.log(self.title + " -> " + str(msg.encode('utf-8')), level=xbmc.LOGNOTICE)
