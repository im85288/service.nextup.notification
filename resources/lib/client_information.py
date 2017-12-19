import xbmcaddon


class ClientInformation():
    def __init__(self):
        addonId = self.getAddonId()
        self.addon = xbmcaddon.Addon(id=addonId)

        self.className = self.__class__.__name__
        self.addonName = self.getAddonName()

    def getAddonId(self):
        # To use when declaring xbmcaddon.Addon(id=addonId)
        return "service.nextup.notification"

    def getAddonName(self):
        # Useful for logging
        return self.addon.getAddonInfo('name').upper()

    def getPlayMode(self):
        if self.addon.getSetting("showPostPlay") == "true":
            return "PostPlay"
        else:
            return "PrePlay"

    def getVersion(self):
        return self.addon.getAddonInfo('version')

