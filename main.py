import sys
import urllib.request
import urllib.error
import urllib.parse
import socket
import random
import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
import xbmcaddon
import json
import base64

# Uncomment this import to enable debugging using the web_pdb addon
import web_pdb;
#
# Dynamic breakpoints are not supported:
# put this line in the code where you want the debugger to break
# web_pdb.set_trace()


addonID = 'plugin.audio.radiobrowser'

# IDs of localizable strings
STRID_TOP_CLICKED = 32000
STRID_TOP_VOTED = 32001
STRID_LAST_CHANGED = 32002
STRID_LAST_CLICKED = 32003
STRID_TAGS = 32004
STRID_COUNTRIES = 32005
STRID_ALL = 32006
STRID_SEARCH = 32007
STRID_MY_STATIONS = 32008
STRID_REMOVE_STATION = 32009
STRID_ADD_STATION = 32010
STRID_SEARCH_STATION = 32011

# Arguments to the add-on call
ARG_MODE = 'mode'
ARG_KEY = 'key'
ARG_VALUE = 'value'
ARG_COUNTRY = 'country'
ARG_UUID = 'stationuuid'
ARG_NAME = 'name'
ARG_URL = 'url'
ARG_FAVICON = 'favicon'
ARG_BITRATE = 'bitrate'

# Values for Mode argument
MODE_PLAY = 'play'
MODE_STATIONS = 'stations'
MODE_TAGS = 'tags'
MODE_COUNTRIES = 'countries'
MODE_STATES = 'states'
MODE_SEARCH = 'search'
MODE_MY_STATIONS = 'mystations'
MODE_ADD_STATION = 'addstation'
MODE_DELETE_STATION = 'delstation'

# Keys in the JSON stations file
JSON_FILE_NAME = 'mystations.json'
JSON_KEY_UUID = 'stationuuid'
JSON_KEY_NAME = 'name'
JSON_KEY_URL = 'url'
JSON_KEY_FAVICON = 'favicon'
JSON_KEY_BITRATE = 'bitrate'
JSON_KEY_STATION_COUNT = 'stationcount'


addon = xbmcaddon.Addon(id=addonID)

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urllib.parse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'songs')

my_stations = {}
profile_dir = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
mystations_file_path = profile_dir + '/' + JSON_FILE_NAME


def get_radiobrowser_base_urls():
    """
    Get all base urls of all currently available radiobrowser servers

    Returns:
    list: a list of strings
    """

    hosts = []
    # get all hosts from DNS
    ips = socket.getaddrinfo('all.api.radio-browser.info',
                             80, 0, 0, socket.IPPROTO_TCP)
    for ip_tupple in ips:
        ip = ip_tupple[4][0]

        # do a reverse lookup on every one of the ips to have a nice name for it
        host_addr = socket.gethostbyaddr(ip)

        # add the name to a list if not already in there
        if host_addr[0] not in hosts:
            hosts.append(host_addr[0])

    # sort list of names
    random.shuffle(hosts)
    # add "https://" in front to make it an url
    xbmc.log("Found hosts: " + ",".join(hosts))
    return list(map(lambda x: "https://" + x, hosts))


def getTranslation(id):
    return addon.getLocalizedString(id).encode('utf-8')


def build_url(query):
    return base_url + '?' + urllib.parse.urlencode(query)


def addLink(stationuuid, name, url, favicon, bitrate):
    #D!
    web_pdb.set_trace()

    li = xbmcgui.ListItem(name)
    li.setArt({'icon': favicon})
    li.setProperty('IsPlayable', 'true')
    li.setInfo(type="Music", infoLabels={"Title":name, "Size":bitrate})
    localUrl = build_url({ARG_MODE: MODE_PLAY,
                          ARG_UUID: stationuuid})

    if stationuuid in my_stations:
        contextTitle = getTranslation(STRID_REMOVE_STATION)
        contextUrl = build_url({ARG_MODE: MODE_DELETE_STATION,
                                ARG_UUID: stationuuid})
    else:
        contextTitle = getTranslation(STRID_ADD_STATION)
        contextUrl = build_url({ARG_MODE: MODE_ADD_STATION,
                                ARG_UUID: stationuuid,
                                ARG_NAME: name.encode('utf-8'),
                                ARG_URL: url,
                                ARG_FAVICON: favicon,
                                ARG_BITRATE: bitrate})

    li.addContextMenuItems([(contextTitle, 'RunPlugin(%s)'%(contextUrl))])

    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=False)


def downloadFile(uri, param):
    """
    Download file with the correct headers set

    Returns:
    a string result
    """

    paramEncoded = None
    if param != None:
        paramEncoded = json.dumps(param)
        xbmc.log('Request to ' + uri + ' Params: ' + ','.join(param))
    else:
        xbmc.log('Request to ' + uri)

    req = urllib.request.Request(uri, paramEncoded)
    req.add_header('User-Agent', 'KodiRadioBrowser/1.2.0')
    req.add_header('Content-Type', 'application/json')
    response = urllib.request.urlopen(req)
    data = response.read().decode('utf-8')

    response.close()
    return data


def downloadApiFile(path, param):
    """
    Download file with relative url from a random api server.
    Retry with other api servers if failed.

    Returns:
    a string result
    """

    servers = get_radiobrowser_base_urls()
    i = 0
    for server_base in servers:
        xbmc.log('Random server: ' + server_base + ' Try: ' + str(i))
        uri = server_base + path

        try:
            data = downloadFile(uri, param)
            return data
        except Exception as e:
            xbmc.log("Unable to download from api url: " + uri, xbmc.LOGERROR)
            pass
        i += 1
    return {}


def addPlayableLink(data):
    dataDecoded = json.loads(data)
    for station in dataDecoded:
        addLink(station[JSON_KEY_UUID],
                station[JSON_KEY_NAME],
                station[JSON_KEY_URL],
                station[JSON_KEY_FAVICON],
                station[JSON_KEY_BITRATE])


def readFile(filepath):
    with open(filepath, 'r') as read_file:
        return json.load(read_file)


def writeFile(filepath, data):
    with open(filepath, 'w') as write_file:
        return json.dump(data, write_file)


def addToMyStations(stationuuid, name, url, favicon, bitrate):
    my_stations[stationuuid] = {JSON_KEY_UUID: stationuuid,
                                JSON_KEY_NAME: name,
                                JSON_KEY_URL: url,
                                JSON_KEY_BITRATE: bitrate,
                                JSON_KEY_FAVICON: favicon}
    writeFile(mystations_file_path, my_stations)


def delFromMyStations(stationuuid):
    if stationuuid in my_stations:
        del my_stations[stationuuid]
        writeFile(mystations_file_path, my_stations)
        xbmc.executebuiltin('Container.Refresh')


# create storage
if not xbmcvfs.exists(profile_dir):
    xbmcvfs.mkdir(profile_dir)

if xbmcvfs.exists(mystations_file_path):
    my_stations = readFile(mystations_file_path)
else:
    writeFile(mystations_file_path, my_stations)

mode = args.get(ARG_MODE, None)

if mode is None:
    localUrl = build_url({ARG_MODE: MODE_STATIONS,
                          ARG_URL: '/json/stations/topclick/100'})
    li = xbmcgui.ListItem(getTranslation(STRID_TOP_CLICKED))
    li.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)

    localUrl = build_url({ARG_MODE: MODE_STATIONS,
                          ARG_URL: '/json/stations/topvote/100'})
    li = xbmcgui.ListItem(getTranslation(STRID_TOP_VOTED))
    li.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)

    localUrl = build_url({ARG_MODE: MODE_STATIONS,
                          ARG_URL: '/json/stations/lastchange/100'})
    li = xbmcgui.ListItem(getTranslation(STRID_LAST_CHANGED))
    li.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)

    localUrl = build_url({ARG_MODE: MODE_STATIONS,
                          ARG_URL: '/json/stations/lastclick/100'})
    li = xbmcgui.ListItem(getTranslation(STRID_LAST_CLICKED))
    li.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)

    localUrl = build_url({ARG_MODE: MODE_TAGS})
    li = xbmcgui.ListItem(getTranslation(STRID_TAGS))
    li.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)

    localUrl = build_url({ARG_MODE: MODE_COUNTRIES})
    li = xbmcgui.ListItem(getTranslation(STRID_COUNTRIES))
    li.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)

    localUrl = build_url({ARG_MODE: MODE_SEARCH})
    li = xbmcgui.ListItem(getTranslation(STRID_SEARCH))
    li.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)

    localUrl = build_url({ARG_MODE: MODE_MY_STATIONS})
    li = xbmcgui.ListItem(getTranslation(STRID_MY_STATIONS))
    li.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == MODE_TAGS:
    data = downloadApiFile('/json/tags', None)
    dataDecoded = json.loads(data)
    for tag in dataDecoded:
        tagName = tag[JSON_KEY_NAME]
        if int(tag[JSON_KEY_STATION_COUNT]) > 1:
            try:
                localUrl = build_url({ARG_MODE: MODE_STATIONS,
                                      ARG_KEY: 'tag',
                                      ARG_VALUE : base64.b32encode(tagName.encode('utf-8'))})
                li = xbmcgui.ListItem(tagName)
                li.setArt({'icon': 'DefaultFolder.png'})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)
            except Exception as e:
                xbmc.err(e)
                pass

    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == MODE_COUNTRIES:
    data = downloadApiFile('/json/countries', None)
    dataDecoded = json.loads(data)
    for tag in dataDecoded:
        countryName = tag[JSON_KEY_NAME]
        if int(tag[JSON_KEY_STATION_COUNT]) > 1:
            try:
                localUrl = build_url({ARG_MODE: MODE_STATES,
                                      ARG_COUNTRY: base64.b32encode(countryName.encode('utf-8'))})
                li = xbmcgui.ListItem(countryName)
                li.setArt({'icon': 'DefaultFolder.png'})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)
            except Exception as e:
                xbmc.log("Stationcount is not of type int", xbmc.LOGERROR)
                pass

    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == MODE_STATES:
    country = args[ARG_COUNTRY][0]
    country = base64.b32decode(country)
    country = country.decode('utf-8')

    data = downloadApiFile('/json/states/' + urllib.parse.quote(country) + '/', None)
    dataDecoded = json.loads(data)

    localUrl = build_url({ARG_MODE: MODE_STATIONS,
                          ARG_KEY: 'country',
                          ARG_VALUE: base64.b32encode(country.encode('utf-8'))})
    li = xbmcgui.ListItem(getTranslation(STRID_ALL))
    li.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)

    for tag in dataDecoded:
        stateName = tag[JSON_KEY_NAME]
        if int(tag[JSON_KEY_STATION_COUNT]) > 1:
            try:
                localUrl = build_url({ARG_MODE: MODE_STATIONS,
                                      ARG_KEY: 'state',
                                      ARG_VALUE: base64.b32encode(stateName.encode('utf-8'))})
                li = xbmcgui.ListItem(stateName)
                li.setArt({'icon': 'DefaultFolder.png'})
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=li, isFolder=True)
            except Exception as e:
                xbmc.log("Stationcount is not of type int", xbmc.LOGERROR)
                pass

    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == MODE_STATIONS:
    url = '/json/stations/search'
    param = None
    if ARG_URL in args:
        url = args[ARG_URL][0]
    else:
        key = args[ARG_KEY][0]
        value = base64.b32decode(args[ARG_VALUE][0])
        value = value.decode('utf-8')
        param = dict({key: value})
        param['order'] = 'clickcount'
        param['reverse'] = True

    data = downloadApiFile(url, param)
    addPlayableLink(data)
    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == MODE_PLAY:
    stationuuid = args[ARG_UUID][0]
    data = downloadApiFile('/json/url/' + str(stationuuid),None)
    dataDecoded = json.loads(data)
    uri = dataDecoded[JSON_KEY_URL]
    xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=uri))

elif mode[0] == MODE_SEARCH:
    dialog = xbmcgui.Dialog()
    d = dialog.input(getTranslation(STRID_SEARCH_STATION), type=xbmcgui.INPUT_ALPHANUM)

    url = '/json/stations/byname/' + urllib.parse.quote(d)
    data = downloadApiFile(url, None)
    addPlayableLink(data)

    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == MODE_MY_STATIONS:
    for station in my_stations.values():
        addLink(station[JSON_KEY_UUID],
                station[JSON_KEY_NAME],
                station[JSON_KEY_URL],
                station[JSON_KEY_FAVICON],
                station[JSON_KEY_BITRATE])

    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_LASTPLAYED)
    xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == MODE_ADD_STATION:
    favicon = args[JSON_KEY_FAVICON][0] if JSON_KEY_FAVICON in args else ''
    addToMyStations(args[JSON_KEY_UUID][0],
                    args[JSON_KEY_NAME][0],
                    args[JSON_KEY_URL][0],
                    favicon,
                    args[JSON_KEY_BITRATE][0])

elif mode[0] == MODE_DELETE_STATION:
    delFromMyStations(args[JSON_KEY_UUID][0])
