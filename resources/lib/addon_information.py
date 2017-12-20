import xbmcaddon


class AddonInformation():
    ADDON_ID = "service.nextup.notification"

    def __init__(self):
        self.addon = xbmcaddon.Addon(id=self.ADDON_ID)
        self.className = self.__class__.__name__
        self.addonName = self.get_addon_name()

    def get_addon(self):
        return self.addon

    def get_addon_name(self):
        # Useful for logging
        return self.get_addon().getAddonInfo('name').upper()

    def get_addon_settings_setting(self, key):
        return self.get_addon().getSetting(key)

    def get_addon_info(self, key):
        return self.get_addon().getAddonInfo(key)

    def get_version(self):
        return self.get_addon().getAddonInfo('version')
