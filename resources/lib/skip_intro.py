import xbmc
import xbmcgui
from platform import machine
from common import Common

ACTION_PLAYER_STOP = 13
OS_MACHINE = machine()


class SkipIntro(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        if OS_MACHINE[0:5] == 'armv7':
            xbmcgui.WindowXMLDialog.__init__(self)
        else:
            xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):
        self.action_exitkeys_id = [10, 13]

    def onClick(self, controlID):
        home_window = Common.get_home_window()
        intro_start = int(home_window.getProperty(Common.INTRO_START))
        intro_length = int(home_window.getProperty(Common.INTRO_LENGTH))

        if controlID == 6012:
            # skip intro selected by user
            xbmc.Player().seekTime(intro_start + intro_length)
            self.close()

        pass
