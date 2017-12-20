import sys

import xbmc

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json


class Utils:
    @staticmethod
    def get_json(method, params):
        json_response = xbmc.executeJSONRPC(
            '{ "jsonrpc": "2.0", "method" : "%s", "params": %s, "id":1 }' % (method, Utils.try_encode(params)))
        jsonobject = json.loads(json_response.decode('utf-8', 'replace'))
        if (jsonobject.has_key('result')):
            jsonobject = jsonobject['result']
            if jsonobject.has_key('movies'):
                return jsonobject['movies']
            elif jsonobject.has_key('tvshows'):
                return jsonobject['tvshows']
            elif jsonobject.has_key('episodes'):
                return jsonobject['episodes']

    @staticmethod
    def try_encode(text, encoding="utf-8"):
        try:
            return text.encode(encoding, "ignore")
        except:
            return text

    @staticmethod
    def try_decode(text, encoding="utf-8"):
        try:
            return text.decode(encoding, "ignore")
        except:
            return text

    @staticmethod
    def unicodetoascii(text):
        result = (text.
                  replace('\xe2\x80\x99', "'").
                  replace('\xc3\xa9', 'e').
                  replace('\xe2\x80\x90', '-').
                  replace('\xe2\x80\x91', '-').
                  replace('\xe2\x80\x92', '-').
                  replace('\xe2\x80\x93', '-').
                  replace('\xe2\x80\x94', '-').
                  replace('\xe2\x80\x94', '-').
                  replace('\xe2\x80\x98', "'").
                  replace('\xe2\x80\x9b', "'").
                  replace('\xe2\x80\x9c', '"').
                  replace('\xe2\x80\x9c', '"').
                  replace('\xe2\x80\x9d', '"').
                  replace('\xe2\x80\x9e', '"').
                  replace('\xe2\x80\x9f', '"').
                  replace('\xe2\x80\xa6', '...').
                  replace('\xe2\x80\xb2', "'").
                  replace('\xe2\x80\xb3', "'").
                  replace('\xe2\x80\xb4', "'").
                  replace('\xe2\x80\xb5', "'").
                  replace('\xe2\x80\xb6', "'").
                  replace('\xe2\x80\xb7', "'").
                  replace('\xe2\x81\xba', "+").
                  replace('\xe2\x81\xbb', "-").
                  replace('\xe2\x81\xbc', "=").
                  replace('\xe2\x81\xbd', "(").
                  replace('\xe2\x81\xbe', ")")
                  )
        return result
