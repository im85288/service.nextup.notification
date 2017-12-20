#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is based on service.skin.widgets
#    Thanks to the original authors

import sys

import xbmc
import xbmcaddon
import xbmcgui

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

__addon__ = xbmcaddon.Addon()


class LibraryFunctions:
    def __init__(self):
        self.WINDOW = xbmcgui.Window(10000)
        self.LIMIT = 20

    # Common properties used by various types of queries
    tvepisode_properties = [
        "title",
        "playcount",
        "season",
        "episode",
        "showtitle",
        "plot",
        "file",
        "rating",
        "resume",
        "tvshowid",
        "art",
        "streamdetails",
        "firstaired",
        "runtime",
        "director",
        "writer",
        "cast",
        "dateadded",
        "lastplayed"]
    tvshow_properties = [
        "title",
        "studio",
        "mpaa",
        "file",
        "art"]

    # Common sort/filter arguments shared by multiple queries
    recent_sort = {"order": "descending", "method": "dateadded"}
    inprogress_filter = {"field": "inprogress", "operator": "true", "value": ""}
    unplayed_filter = {"field": "playcount", "operator": "lessthan", "value": "1"}
    specials_filter = {"field": "season", "operator": "greaterthan", "value": "0"}

    # Construct a JSON query string from the arguments, execute it, return UTF8
    def json_query(self, method, unplayed=False, include_specials=True, properties=None, sort=False,
                   query_filter=False, limit=False, params=False):
        # Set defaults if not all arguments are passed in
        if sort is False:
            sort = {"method": "random"}
        if properties is None:
            properties = self.tvshow_properties
        if unplayed:
            query_filter = self.unplayed_filter if not query_filter else {"and": [self.unplayed_filter, query_filter]}
        if not include_specials:
            query_filter = self.specials_filter if not query_filter else {"and": [self.specials_filter, query_filter]}

        json_query = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {}}

        # As noted in the docstring, False = use a default, None=omit entirely
        if properties is not None:
            json_query["params"]["properties"] = properties
        if limit is not None:
            json_query["params"]["limits"] = {"end": limit if limit else self.LIMIT}
        if sort is not None:
            json_query["params"]["sort"] = sort
        if query_filter:
            json_query["params"]["filter"] = query_filter
        if params:
            json_query["params"].update(params)

        json_string = json.dumps(json_query)
        rv = xbmc.executeJSONRPC(json_string)

        return unicode(rv, 'utf-8', errors='ignore')

    # Recommended episodes: Earliest unwatched episode from in-progress shows
    def fetch_recommended_episodes(self):
        # First we get a list of all the in-progress TV shows.
        json_query_string = self.json_query("VideoLibrary.GetTVShows", unplayed=True,
                                            properties=self.tvshow_properties,
                                            sort={"order": "descending",
                                                  "method": "lastplayed"},
                                            query_filter=self.inprogress_filter)
        json_query = json.loads(json_query_string)

        # If we found any, find the oldest unwatched show for each one.
        if "result" in json_query and 'tvshows' in json_query['result']:
            for item in json_query['result']['tvshows']:
                if xbmc.abortRequested:
                    break
                json_query2 = self.json_query("VideoLibrary.GetEpisodes", unplayed=True,
                                              include_specials=True,
                                              properties=self.tvepisode_properties,
                                              sort={"method": "episode"}, limit=1,
                                              params={"tvshowid": item['tvshowid']})
                self.WINDOW.setProperty("recommended-episodes-data-%d"
                                        % item['tvshowid'], json_query2)
        return json_query_string

    def get_now_playing(self):
        # Get the active player
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
        result = unicode(result, 'utf-8', errors='ignore')
        result = json.loads(result)

        # Seems to work too fast loop whilst waiting for it to become active
        while not result["result"]:
            result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
            result = unicode(result, 'utf-8', errors='ignore')
            result = json.loads(result)

        if 'result' in result and result["result"][0] is not None:
            playerid = result["result"][0]["playerid"]
            # Get details of the playing media
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str(
                    playerid) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount","genre"] } }')
            result = unicode(result, 'utf-8', errors='ignore')
            result = json.loads(result)
            return result

    def showtitle_to_id(self, title):
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "properties": ["title"]
            },
            "id": "libTvShows"
        }
        try:
            json_result = json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))
            if 'result' in json_result and 'tvshows' in json_result['result']:
                json_result = json_result['result']['tvshows']
                for tvshow in json_result:
                    if tvshow['label'] == title:
                        return tvshow['tvshowid']
            return '-1'
        except Exception:
            return '-1'

    def get_episode_id(self, showid, showseason, showepisode):
        showseason = int(showseason)
        showepisode = int(showepisode)
        episodeid = 0
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetEpisodes",
            "params": {
                "properties": ["season", "episode"],
                "tvshowid": int(showid)
            },
            "id": "1"
        }
        try:
            json_result = json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))
            if 'result' in json_result and 'episodes' in json_result['result']:
                json_result = json_result['result']['episodes']
                for episode in json_result:
                    if episode['season'] == showseason and episode['episode'] == showepisode:
                        if 'episodeid' in episode:
                            episodeid = episode['episodeid']
            return episodeid
        except Exception:
            return episodeid

    def parse_tvshows_recommended(self, limit):
        items = []
        prefix = "recommended-episodes"
        json_query = self.fetch_recommended_episodes()

        if json_query:
            # First unplayed episode of recent played tvshows
            json_query = json.loads(json_query)
            if "result" in json_query and 'tvshows' in json_query['result']:
                count = -1
                for item in json_query['result']['tvshows']:
                    if xbmc.abortRequested:
                        break
                    if count == -1:
                        count += 1
                        continue
                    json_query2 = xbmcgui.Window(10000).getProperty(prefix + "-data-" + str(item['tvshowid']))
                    if json_query2:
                        json_query2 = json.loads(json_query2)
                        if "result" in json_query2 and json_query2['result'] is not None and 'episodes' in json_query2[
                            'result']:
                            for item2 in json_query2['result']['episodes']:
                                episode = "%.2d" % float(item2['episode'])
                                season = "%.2d" % float(item2['season'])
                                episodeno = "s%se%s" % (season, episode)
                                break
                            plot = item2['plot']
                            episodeid = str(item2['episodeid'])
                            if len(item['studio']) > 0:
                                studio = item['studio'][0]
                            else:
                                studio = ""
                            if "director" in item2:
                                director = " / ".join(item2['director'])
                            if "writer" in item2:
                                writer = " / ".join(item2['writer'])

                            liz = xbmcgui.ListItem(item2['title'])
                            liz.setPath(item2['file'])
                            liz.setProperty('IsPlayable', 'true')
                            liz.setInfo(type="Video", infoLabels={"Title": item2['title'],
                                                                  "Episode": item2['episode'],
                                                                  "Season": item2['season'],
                                                                  "Studio": studio,
                                                                  "Premiered": item2['firstaired'],
                                                                  "Plot": plot,
                                                                  "TVshowTitle": item2['showtitle'],
                                                                  "Rating": str(float(item2['rating'])),
                                                                  "MPAA": item['mpaa'],
                                                                  "Playcount": item2['playcount'],
                                                                  "Director": director,
                                                                  "Writer": writer,
                                                                  "mediatype": "episode"})
                            liz.setProperty("episodeid", episodeid)
                            liz.setProperty("episodeno", episodeno)
                            liz.setProperty("resumetime", str(item2['resume']['position']))
                            liz.setProperty("totaltime", str(item2['resume']['total']))
                            liz.setProperty("type", 'episode')
                            liz.setProperty("fanart_image", item2['art'].get('tvshow.fanart', ''))
                            liz.setProperty("dbid", str(item2['episodeid']))
                            liz.setArt(item2['art'])
                            liz.setThumbnailImage(item2['art'].get('thumb', ''))
                            liz.setIconImage('DefaultTVShows.png')
                            hasVideo = False
                            for key, value in item2['streamdetails'].iteritems():
                                for stream in value:
                                    if 'video' in key:
                                        hasVideo = True
                                    liz.addStreamInfo(key, stream)

                            # if duration wasnt in the streaminfo try adding the scraped one
                            if not hasVideo:
                                stream = {'duration': item2['runtime']}
                                liz.addStreamInfo("video", stream)

                            items.append(liz)

                            count += 1
                            if count == limit:
                                break
                    if count == limit:
                        break
            del json_query
        return items
