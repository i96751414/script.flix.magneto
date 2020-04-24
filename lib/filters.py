import re
from collections import namedtuple

Filter = namedtuple("Filter", "name regex")


def _compile(pattern):
    return re.compile(r"[\b_](?:{})".format(pattern), flags=re.IGNORECASE)


class FilterBase(object):
    values = ()

    @classmethod
    def match(cls, string):
        for v in cls.values:
            if v.regex.search(string):
                return v.name


class Resolution(FilterBase):
    r_240p = Filter("240p", _compile("240p?|tvrip|satrip|vhsrip"))
    r_480p = Filter("480p", _compile("480p?|xvid|dvd|dvdrip|hdtv"))
    r_720p = Filter("720p", _compile("720p?|hdrip|bluray|b[rd]rip"))
    r_1080p = Filter("1080p", _compile("1080p?|fullhd|fhd"))
    r_2k = Filter("2K", _compile("2k|1440p?"))
    r_4k = Filter("4K", _compile("4k|2160p?"))

    values = (r_240p, r_480p, r_720p, r_1080p, r_2k, r_4k)


class ReleaseType(FilterBase):
    r_brrip = Filter("BRRip", _compile("b[rd]rip|bluray"))
    r_webdl = Filter("WebDL", _compile("web[^a-zA-z0-9]*(?:dl|rip)"))
    r_hdrip = Filter("HDRip", _compile("hdrip"))
    r_hdtv = Filter("HDTV", _compile("hdtv"))
    r_dvd = Filter("DVDRip", _compile("dvd[^a-zA-z0-9]*rip"))
    r_dvdscr = Filter("DVDScreener", _compile("dvd[^a-zA-z0-9]*scr"))
    r_screener = Filter("Screener", _compile("screener|scr"))
    r_3d = Filter("3D", _compile("3d"))
    r_telesync = Filter("TeleSync", _compile("telesync|ts"))
    r_telecine = Filter("TeleCine", _compile("telecine|tc"))
    r_cam = Filter("CAM", _compile("cam|camrip|hdcam"))
    r_tvrip = Filter("TVRip", _compile("(?:tv|sat)rip"))
    r_vhsrip = Filter("VHSrip", _compile("vhsrip"))
    r_trailer = Filter("Trailer", _compile("trailer"))
    r_workprint = Filter("Workprint", _compile("workprint"))

    values = (r_brrip, r_webdl, r_hdrip, r_hdtv, r_dvd, r_dvdscr, r_screener, r_3d,
              r_telesync, r_telecine, r_cam, r_tvrip, r_vhsrip, r_trailer, r_workprint)


class SceneTags(FilterBase):
    t_nuked = Filter("Nuked", _compile("nuked"))
    t_proper = Filter("Proper", _compile("proper"))

    values = (t_nuked, t_proper)


class VideoCodecs(FilterBase):
    c_xvid = Filter("Xvid", _compile("xvid"))
    c_h264 = Filter("H.264", _compile("[hx]264"))
    c_h265 = Filter("H.265", _compile("[hx]265|hevc"))

    values = (c_xvid, c_h264, c_h265)


class AudioCodecs(FilterBase):
    c_mp3 = Filter("MP3", _compile("mp3"))
    c_aac = Filter("AAC", _compile("aac"))
    c_ac3 = Filter("AC3", _compile("ac3|[Dd]*5[^a-zA-z0-9]+1"))
    c_dts = Filter("DTS", _compile("dts"))
    c_dts_hd = Filter("DTS HD", _compile("dts[^a-zA-z0-9]+hd"))
    c_dts_hd_ma = Filter("DTS HD MA", _compile("dts[^a-zA-z0-9]+hd[^a-zA-z0-9]+ma"))

    values = (c_mp3, c_aac, c_ac3, c_dts, c_dts_hd, c_dts_hd_ma)
