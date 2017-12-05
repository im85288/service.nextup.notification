import xbmc
import xbmcgui
from platform import machine

ACTION_PLAYER_STOP = 13
OS_MACHINE = machine()


class SkipIntro(xbmcgui.WindowXMLDialog):
    item = None
    skipintro = False

    def __init__(self, *args, **kwargs):
        if OS_MACHINE[0:5] == 'armv7':
            xbmcgui.WindowXMLDialog.__init__(self)
        else:
            xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):
        self.action_exitkeys_id = [10, 13]

    def setSkipIntro(self, skipintro):
        self.skipintro = skipintro

    def isSkipIntro(self):
        return self.skipintro

    def onClick(self, controlID):

        xbmc.log('skip intro onclick: ' + str(controlID))

        if controlID == 6012:
            # watch now
            self.setSkipIntro(True)
            self.close()

        pass

    def onAction(self, action):

        xbmc.log('skip intro action: ' + str(action.getId()))
        if action == ACTION_PLAYER_STOP:
            self.close()
