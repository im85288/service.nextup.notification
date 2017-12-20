import time

import xbmc
import xbmcgui

from addon_information import AddonInformation
from addon_settings import AddonSettings
from common import Common
from logger import Logger
from player import Player
from skip_intro import SkipIntro


class PlaybackMonitor:
    def __init__(self):
        self.logger = Logger("%s %s" % (self.addonName, self.__class__.__name__))
        self.logger.log("Starting Playback Monitior", 0)
        self.addon_information = AddonInformation()
        self.addon_settings = AddonSettings()
        self.home_window = Common.get_home_window()
        self.player = Player()
        self.last_file = None
        self.last_unwatched_file = None
        self._refresh_dynamic_values()

    def _refresh_dynamic_values(self):
        self.notification_time = self.addon_settings.get_auto_play_season_time()
        self.next_up_disabled = self.addon_settings.is_disable_next_up()
        self.next_up_skip_enabled = self.addon_settings.is_enable_next_up_skip()
        self.next_up_skip_enabled_auto = self.addon_settings.is_enable_auto_skip()
        self.next_up_skip_enabled_3rd_p = self.addon_settings.is_enable_next_up_skip_3rd_party()
        self.next_up_skip_enabled_no_pause = self.addon_settings.is_enable_next_up_skip_no_pause()
        self.random_unwatched_time = self.addon_settings.get_display_random_unwatched_time()
        self.display_random_unwatched = self.addon_settings.is_display_random_unwatched()
        self.show_post_play = self.addon_settings.is_show_post_play()
        self.show_post_play_preview = self.addon_settings.is_show_post_play_preview()

    def monitor_playback(self):
        try:
            self._refresh_dynamic_values()
            if self.home_window.getProperty(Common.UN_SKIPPED) == "True" and (
                        self.next_up_skip_enabled or self.next_up_skip_enabled_3rd_p):
                self.handle_skip_intro()
            if self.home_window.getProperty(Common.PSEUDO_TV_RUNNING) != "True" and not self.next_up_disabled:
                self.handle_next_up()
        except Exception as e:
            self.logger.log("Exception in Playback Monitor Service: %s" % e)

    def handle_next_up(self):
        current_play_time = xbmc.Player().getTime()
        current_total_time = xbmc.Player().getTotalTime()
        current_file = xbmc.Player().getPlayingFile()
        if (not self.show_post_play or (self.show_post_play_preview and self.show_post_play)) and (
                            current_total_time - current_play_time <= int(self.notification_time) and (
                                self.last_file is None or self.last_file != current_file)) and current_total_time != 0:
            self.last_file = current_file
            self.logger.log(
                "Calling autoplayback totaltime - playtime is %s" % (current_total_time - current_play_time), 2)
            self.player.autoPlayPlayback()
            self.logger.log("Netflix style autoplay succeeded.", 2)

        if (self.show_post_play and not self.show_post_play_preview) and (
                        current_total_time - current_play_time <= 10) and current_total_time != 0:
            self.logger.log("Calling post playback", 2)
            self.player.postPlayPlayback()

        if self.display_random_unwatched and (int(current_play_time) >= int(self.random_unwatched_time)) and (
                    int(current_play_time) < int(int(self.random_unwatched_time) + 100)) and (
                        self.last_unwatched_file is None or self.last_unwatched_file != current_file):
            self.logger.log("randomunwatchedtime is %s" % (int(self.random_unwatched_time)), 2)
            self.logger.log("Calling display unwatched", 2)
            self.last_unwatched_file = current_file
            self.player.displayRandomUnwatched()

    def handle_skip_intro(self):
        current_play_time = xbmc.Player().getTime()
        intro_start = int(self.home_window.getProperty(Common.INTRO_START))
        intro_length = int(self.home_window.getProperty(Common.INTRO_LENGTH))
        self.logger.log(
            "skip intro check playtime is " + str(current_play_time) + " introstart is " + str(intro_start),
            1)
        if (intro_start == 99999) or (intro_length == 0) or (intro_length == 99999):
            self.logger.log(
                "Intro not set for episode (start=%s / length=%s) -> disable checks for this episode" %
                (str(intro_start), str(intro_length)), 1)
            self.home_window.clearProperty(Common.UN_SKIPPED)
        if (current_play_time >= intro_start) and (current_play_time < (current_play_time + intro_length)):
            if self.next_up_skip_enabled_auto == 1:
                dlg = xbmcgui.Dialog()
                dlg.notification("Nextup Service Notification", 'Skipping Intro...',
                                 xbmcgui.NOTIFICATION_INFO, 5000)

                if self.next_up_skip_enabled_no_pause == 1:
                    xbmc.Player().seekTime(intro_start + intro_length)
                    self.home_window.clearProperty(Common.UN_SKIPPED)
                else:
                    xbmc.Player().pause()
                    time.sleep(1)  # give kodi the chance to execute
                    xbmc.Player().seekTime(intro_start + intro_length)
                    time.sleep(1)  # give kodi the chance to execute
                    xbmc.Player().pause()  # unpause playback at seek position
                    self.home_window.clearProperty(Common.UN_SKIPPED)
            else:
                skip_intro_page = SkipIntro("script-nextup-notification-SkipIntro.xml",
                                            self.addon_information.get_addon_info('path'), "default", "1080i")
                # close skip intro dialog after time
                xbmc.executebuiltin('AlarmClock(closedialog,Dialog.Close(all,true),00:15,silent)')
                self.logger.log("showing skip intro page")
                self.home_window.clearProperty(Common.UN_SKIPPED)
                skip_intro_page.show()
