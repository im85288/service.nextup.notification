from addon_information import AddonInformation


class AddonSettings:
    AUTO_PLAY_SEASON_TIME = "autoPlaySeasonTime"
    DISABLE_NEXT_UP = "disableNextUp"
    ENABLE_NEXT_UP_SKIP = "enableNextUpSkip"
    ENABLE_AUTO_SKIP = "enableAutoSkip"
    ENABLE_NEXT_UP_SKIP_3RD_P = "enableNextUpSkip3rdP"
    ENABLE_NEXT_UP_SKIP_NO_PAUSE = "enableNextUpSkipNoPause"
    DISPLAY_RANDOM_UNWATCHED_TIME = "displayRandomUnwatchedTime"
    DISPLAY_RANDOM_UNWATCHED = "displayRandomUnwatched"
    SHOW_POST_PLAY = "showPostPlay"
    SHOW_POST_PLAY_PREVIEW = "showPostPlayPreview"

    def __init__(self):
        self.addon_information = AddonInformation

    def get_setting(self, key):
        return self.addon_information.get_addon().getSetting(key)

    def set_setting(self, key, value):
        self.addon_information.get_addon().setSetting(key, value)

    def is_setting(self, key):
        return self.get_setting(key).lower() == "true"

    def get_auto_play_season_time(self):
        return self.get_setting(self.AUTO_PLAY_SEASON_TIME)

    def is_disable_next_up(self):
        return self.is_setting(self.DISABLE_NEXT_UP)

    def is_enable_next_up_skip(self):
        return self.is_setting(self.ENABLE_NEXT_UP_SKIP)

    def is_enable_auto_skip(self):
        return self.is_setting(self.ENABLE_AUTO_SKIP)

    def is_enable_next_up_skip_3rd_party(self):
        return self.is_setting(self.ENABLE_NEXT_UP_SKIP_3RD_P)

    def is_enable_next_up_skip_no_pause(self):
        return self.is_setting(self.ENABLE_NEXT_UP_SKIP_NO_PAUSE)

    def get_display_random_unwatched_time(self):
        return self.is_setting(self.DISPLAY_RANDOM_UNWATCHED_TIME)

    def is_display_random_unwatched(self):
        return self.is_setting(self.DISPLAY_RANDOM_UNWATCHED)

    def is_show_post_play(self):
        return self.is_setting(self.SHOW_POST_PLAY)

    def is_show_post_play_preview(self):
        return self.is_setting(self.SHOW_POST_PLAY_PREVIEW)
