import xbmcaddon
import xbmc
import xbmcgui
import os
import threading
import json
from datetime import datetime
import time

cwd = xbmcaddon.Addon(id='service.nextup.notification').getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( cwd, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)

import Utils as utils
from Player import Player
from ClientInformation import ClientInformation

class Service():
    

    clientInfo = ClientInformation()
    addonName = clientInfo.getAddonName()
    WINDOW = xbmcgui.Window(10000)
    
    def __init__(self, *args ):
        addonName = self.addonName

        self.logMsg("Starting NextUp Service", 0)
        self.logMsg("======== START %s ========" % addonName, 0)
        self.logMsg("KODI Version: %s" % xbmc.getInfoLabel("System.BuildVersion"), 0)
        self.logMsg("%s Version: %s" % (addonName, self.clientInfo.getVersion()), 0)
        self.logMsg("Platform: %s" % (self.clientInfo.getPlatform()), 0)
        

    def logMsg(self, msg, lvl=1):
        
        className = self.__class__.__name__
        utils.logMsg("%s %s" % (self.addonName, className), str(msg), int(lvl))
            
    def ServiceEntryPoint(self):
        
        lastProgressUpdate = datetime.today()
        player = Player()
        
        lastFile = None
        
        while not xbmc.abortRequested :
            if xbmc.Player().isPlaying():
                try:
                    playTime = xbmc.Player().getTime()
                    totalTime = xbmc.Player().getTotalTime()
                    currentFile = xbmc.Player().getPlayingFile()
                    addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                    notificationtime = addonSettings.getSetting("autoPlaySeasonTime")
                    if (totalTime - playTime <= int(notificationtime) and (lastFile==None or lastFile!=currentFile)):
                        lastFile = currentFile
                        player.autoPlayPlayback()
                        self.logMsg("Netflix style autoplay succeeded.", 2)
                            
                except Exception, e:
                    self.logMsg("Exception in Playback Monitor Service: %s" % e)
                    pass

        self.logMsg("======== STOP %s ========" % self.addonName, 0)
       
#start the service
Service().ServiceEntryPoint()
