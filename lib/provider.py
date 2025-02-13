import logging
import os

try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus

from xbmcgui import DialogProgressBG

from flix.kodi import ADDON_PATH, ADDON_NAME, get_boolean_setting, get_int_setting, translate
from flix.provider import Provider, ProviderResult
from lib.filters import Unknown, Resolution, ReleaseType, SceneTags, VideoCodec, AudioCodec
from lib.scraper import Scraper, ScraperRunner, default_session
from lib.utils import CachedCall, Title, Magnet, InvalidMagnet, resolution_colors, colored_text, bold


class Result(object):
    def __init__(self, scraper, result):
        self._providers = {self._get_scraper_name(scraper)}
        self._icon = scraper.get_attribute("icon", default=None)
        self._title = result["title"]
        self._magnet = result["magnet"]
        self._seeds = []
        self._leeches = []
        self._size = None
        self._resolution = self._release = self._scene = self._video_codec = self._audio_codec = Unknown
        self._get_optional_fields(result)
        self._get_filters(result)

    @staticmethod
    def _get_scraper_name(scraper):
        color = scraper.get_attribute("color", default=None)
        if color is None:
            return scraper.name
        return colored_text(scraper.name, color)

    def _get_optional_fields(self, result):
        for field_name, values in (("seeds", self._seeds), ("leeches", self._leeches)):
            try:
                value = result.get(field_name)
                if value is not None:
                    values.append(int(value))
            except ValueError:
                pass

        if self._size is None:
            self._size = result.get("size")

    def _get_filters(self, result):
        title = result["title"]
        for field, filter_obj in (("_resolution", Resolution), ("_release", ReleaseType), ("_scene", SceneTags),
                                  ("_video_codec", VideoCodec), ("_audio_codec", AudioCodec)):
            if getattr(self, field) is Unknown:
                setattr(self, field, filter_obj.match(title))

    def add_result(self, scraper, result):
        self._providers.add(self._get_scraper_name(scraper))
        self._get_optional_fields(result)
        self._get_filters(result)

    @property
    def seeds(self):
        return (sum(self._seeds) // len(self._seeds)) if self._seeds else None

    @property
    def leeches(self):
        return (sum(self._leeches) // len(self._leeches)) if self._leeches else None

    @property
    def size(self):
        return self._size

    @property
    def resolution(self):
        return self._resolution

    @property
    def release(self):
        return self._release

    def to_provider_result(self):
        label = []
        if self._resolution is not Unknown:
            label.append(bold(colored_text(self._resolution.name, resolution_colors[self._resolution.name])))
        if self._seeds and self._leeches:
            label.append("({}/{}) ".format(self.seeds, self.leeches))
        if self._size is not None:
            label.append(bold("[{}]".format(self._size)))
        for field in (self._release, self._video_codec, self._audio_codec):
            if field is not Unknown:
                label.append(field.name)
        if label:
            label.append("-")
        label.extend(sorted(self._providers))
        icon = os.path.join(ADDON_PATH, "resources", self._icon) if self._icon else None

        return ProviderResult(
            label=" ".join(label),
            label2=self._title,
            icon=icon,
            url="plugin://plugin.video.torrest/play_magnet?magnet={}".format(quote_plus(self._magnet)),
        )

    def get_factor(self, seeds_factor=4, default_seeds=0, leeches_factor=1, default_leeches=0, default_resolution=2):
        seeds = self.seeds if self._seeds else default_seeds
        leeches = self.leeches if self._leeches else default_leeches
        resolution = default_resolution if self._resolution is Unknown else self._resolution.factor
        return max(seeds * seeds_factor + leeches * leeches_factor, 1) * resolution


def include_result(result, get_setting=CachedCall(get_boolean_setting)):
    return ((not get_setting("require_size") or bool(result.size)) and
            (not get_setting("require_seeds") or bool(result.seeds)) and
            (not get_setting("require_resolution") or get_setting(
                "include_resolution_{}".format(result.resolution.name.lower()))) and
            (not get_setting("require_release_type") or get_setting(
                "include_release_{}".format(result.release.name.lower()))))


def perform_search(search_type, data):
    results = {}
    with default_session() as session:
        scrapers = [s for s in Scraper.get_scrapers(os.path.join(ADDON_PATH, "resources", "providers.json"),
                                                    timeout=get_int_setting("scraper_timeout"), session=session)
                    if get_boolean_setting(s.id)]

        if not scrapers:
            logging.warning("No scrapers configured/enabled")
            return None

        runner_class = ProgressScraperRunner if get_boolean_setting("enable_bg_dialog") else ScraperRunner
        with runner_class(scrapers, num_threads=get_int_setting("thread_number")) as runner:
            runner_data = runner.parse_query(data) if search_type == "query" else runner.parse(search_type, data)

            for scraper, scraper_results in runner_data:
                logging.debug("Processing %s scraper results", scraper.name)
                for scraper_result in scraper_results:
                    try:
                        info_hash = Magnet.from_string(scraper_result["magnet"]).info_hash
                    except InvalidMagnet:
                        continue
                    if info_hash == "0" * 40:
                        continue

                    magnet_result = results.get(info_hash)
                    if magnet_result is None:
                        results[info_hash] = Result(scraper, scraper_result)
                    else:
                        magnet_result.add_result(scraper, scraper_result)

    # noinspection PyTypeChecker
    return [
        r.to_provider_result()
        for r in sorted(results.values(), key=Result.get_factor, reverse=True)
        if include_result(r)
    ]


class ProgressScraperRunner(ScraperRunner):
    def __init__(self, scrapers, num_threads=10):
        super(ProgressScraperRunner, self).__init__(scrapers, num_threads=num_threads)
        self._progress = DialogProgressBG()
        self._index = 0
        self._total = len(scrapers)
        self._message = translate(30100)
        self._progress.create(ADDON_NAME, message=self._message)

    def before_result(self, scraper):
        self._progress.update(self._index * 100 // self._total, message=self._message + ": " + scraper.name)
        self._index += 1

    def close(self):
        super(ProgressScraperRunner, self).close()
        if self._progress is not None:
            self._progress.close()
            self._progress = None


class MagnetoProvider(Provider):
    def search(self, query):
        return perform_search("query", query)

    def search_movie(self, tmdb_id, title, titles, year=None):
        return perform_search("movie", dict(tmdb_id=tmdb_id, title=Title(title, titles), year=year or ""))

    def search_show(self, tmdb_id, show_title, titles, year=None):
        return perform_search("show", dict(tmdb_id=tmdb_id, title=Title(show_title, titles), year=year or ""))

    def search_season(self, tmdb_id, show_title, season_number, titles):
        return perform_search("season", dict(tmdb_id=tmdb_id, title=Title(show_title, titles), season=season_number))

    def search_episode(self, tmdb_id, show_title, season_number, episode_number, titles):
        return perform_search("episode", dict(
            tmdb_id=tmdb_id, title=Title(show_title, titles), season=season_number, episode=episode_number))

    def resolve(self, provider_data):
        raise NotImplementedError("Resolve method can't be called on this provider")
