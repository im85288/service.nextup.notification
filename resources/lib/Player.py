import xbmcaddon
import xbmcplugin
import xbmc
import xbmcgui
import os
import threading
import json
import inspect

import Utils as utils

from ClientInformation import ClientInformation
from NextUpInfo import NextUpInfo

# service class for playback monitoring
class Player( xbmc.Player ):

    # Borg - multiple instances, shared state
    _shared_state = {}
    
    xbmcplayer = xbmc.Player()
    clientInfo = ClientInformation()
    
    addonName = clientInfo.getAddonName()
    addonId = clientInfo.getAddonId()
    addon = xbmcaddon.Addon(id=addonId)

    logLevel = 0
    played_information = {}
    settings = None
    playStats = {}
    
    def __init__( self, *args ):
        
        self.__dict__ = self._shared_state
        self.logMsg("Starting playback monitor service", 1)
        
    def logMsg(self, msg, lvl=1):
        
        self.className = self.__class__.__name__
        utils.logMsg("%s %s" % (self.addonName, self.className), msg, int(lvl))      
        
    
    def autoPlayPlayback(self):
        currentFile = xbmc.Player().getPlayingFile()
    
        # Get the active player
        result = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}' )
        result = unicode(result, 'utf-8', errors='ignore')
        self.logMsg( "Got active player "+ result ,2)
        result = json.loads(result)
        
        # Seems to work too fast loop whilst waiting for it to become active
        while result["result"] == []:
            result = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}' )
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg( "Got active player "+ result ,2)
            result = json.loads(result)
        
        if result.has_key('result') and result["result"][0] != None:
            playerid = result[ "result" ][ 0 ][ "playerid" ]
            
            # Get details of the playing media
            self.logMsg( "Getting details of playing media" ,1)
            result = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str( playerid ) + ', "properties": [ "tvshowid" ] } }' )
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg( "Got details of playing media" + result,2)
            
            result = json.loads(result)
            if result.has_key( 'result' ):
                type = result[ "result" ][ "item" ][ "type" ]
                if type == "episode":
                    # Get the next up episode
                    addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                    playMode = addonSettings.getSetting("autoPlayMode")
                    tvshowid = result[ "result" ][ "item" ][ "tvshowid" ]
                    self.logMsg( "Getting details of next up episode for tvshow id: "+str(tvshowid) ,1)
                    
                    result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %d, "sort": {"method":"episode"}, "filter": {"field": "playcount", "operator": "lessthan", "value":"1"}, "properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", "file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", "dateadded", "lastplayed" ], "limits":{"start":1,"end":2}}, "id": "1"}' %tvshowid)
                    self.logMsg( "Got earlier details of next up episode" + result,2)
                    if result:
                    
                        result = unicode(result, 'utf-8', errors='ignore')
                        result = json.loads(result)
                        self.logMsg( "Got details of next up episode %s" % str(result),2)
                        xbmc.sleep( 100 )
                        
                        # Find the next unwatched and the newest added episodes
                        if result.has_key( "result" ) and result[ "result" ].has_key( "episodes" ):
                            episode = result[ "result" ][ "episodes" ][0]
                            self.logMsg( "episode details %s" % str(episode),2)
                            if episode[ "playcount" ] == 0:
                                    # we have a next up episode
                                    pDialog = xbmcgui.DialogProgress()
                                    nextUpPage = NextUpInfo("NextUpInfo.xml", addonSettings.getAddonInfo('path'), "default", "720p")
                                    nextUpPage.setItem(episode)
                                    playTime = xbmc.Player().getTime()
                                    totalTime = xbmc.Player().getTotalTime()
                                    nextUpPage.show()
                                    playTime = xbmc.Player().getTime()
                                    totalTime = xbmc.Player().getTotalTime()
                                    while xbmc.Player().isPlaying() and (totalTime-playTime > 1) and not nextUpPage.isCancel() and not nextUpPage.isWatchNow():
                                        xbmc.sleep(100)
                                        playTime = xbmc.Player().getTime()
                                        totalTime = xbmc.Player().getTotalTime()
                                    nextUpPage.close()
                                    if (not nextUpPage.isCancel() and playMode =="0") or (nextUpPage.isWatchNow() and playMode=="1"):
                                        self.logMsg( "playing media episode id %s" % str(episode["episodeid"]),2)
                                        # Play media
                                        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"episodeid": ' + str(episode["episodeid"]) + '} } }' )
            
