import xbmc
import xbmcgui


class Common:
    UN_SKIPPED = "NextUpNotification.Unskipped"
    INTRO_START = "NextUpNotification.intro_start"
    INTRO_LENGTH = "NextUpNotification.intro_length"
    PSEUDO_TV_RUNNING = "PseudoTVRunning"
    KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])

    @staticmethod
    def get_home_window():
        return xbmcgui.Window(10000)
