import xbmc
import xbmcgui
from platform import machine

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

        introStart = int(xbmcgui.Window(10000).getProperty("NextUpNotification.introStart"))
        introLength = int(xbmcgui.Window(10000).getProperty("NextUpNotification.introLength"))

        if controlID == 6012:
            # skip intro selected by user
            xbmc.Player().seekTime(introStart+introLength)
            self.close()

        pass
