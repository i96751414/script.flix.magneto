from collections import namedtuple

Filter = namedtuple("Filter", "name keywords")


class Resolution(object):
    r_240p = Filter("240p", ("240p", "tvrip", "satrip", "vhsrip"))
    r_480p = Filter("480p", ("480p", "xvid", "dvd", "dvdrip", "hdtv"))
    r_720p = Filter("720p", ("720p", "hdrip", "bluray", "brrip", "bdrip"))
    r_1080p = Filter("1080p", ("1080p", "fullhd", "_fhd_"))
    r_2k = Filter("2K", ("_2k_", "1440p"))
    r_4k = Filter("4K", ("_4k_", "2160p"))


class ReleaseType(object):
    r_brrip = Filter("BRRip", ("brrip", "bdrip", "bluray"))
    r_webdl = Filter("WEB-DL", ("webdl", "webrip", "web_dl", "dlrip", "_yts_"))
    r_hdrip = Filter("HDrip", ("hdrip",))
    r_hdtv = Filter("HDTV", ("hdtv",))
    r_dvd = Filter("DVD", ("_dvd_", "dvdrip"))
    r_dvdscr = Filter("DVDscr", ("dvdscr",))
    r_screener = Filter("Screener", ("screener", "_scr_"))
    r_3d = Filter("3D", ("_3d_",))
    r_telesync = Filter("TS", ("telesync", "_ts_", "_tc_"))
    r_cam = Filter("CAM", ("_cam_", "hdcam"))
    r_tvrip = Filter("TVRip", ("tvrip", "satrip"))
    r_vhsrip = Filter("VHSrip", ("vhsrip",))
    r_trailer = Filter("Trailer", ("trailer",))
    r_workprint = Filter("Workprint", ("workprint",))
