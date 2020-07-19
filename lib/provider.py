import os

try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus

from flix.kodi import ADDON_PATH, get_boolean_setting
from flix.provider import Provider, ProviderResult
from lib.filters import Unknown, Resolution, ReleaseType, SceneTags, VideoCodec, AudioCodec
from lib.scraper import Scraper, ScraperRunner
from lib.utils import Title, Magnet, InvalidMagnet, resolution_colors, colored_text, bold


class Result(object):
    def __init__(self, scraper, result):
        self._providers = {self._get_scraper_name(scraper)}
        self._icon = scraper.get_attribute("icon")
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
        for field in ("seeds", "leeches"):
            try:
                value = result.get(field)
                if value is not None:
                    getattr(self, "_" + field).append(int(value))
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

    def to_provider_result(self):
        label = []
        if self._resolution is not Unknown:
            label.append(bold(colored_text(self._resolution.name, resolution_colors[self._resolution.name])))
        if self._seeds and self._leeches:
            label.append("({}/{}) ".format(self.seeds, self.leeches))
        if self._size is not None:
            label.append(bold("[{}]".format(sizeof(int(self._size)))))
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


def perform_search(search_type, data, num_threads=10):
    results = {}
    scrapers = [s for s in Scraper.get_scrapers(os.path.join(ADDON_PATH, "resources", "providers.json"))
                if get_boolean_setting(s.id)]
    with ScraperRunner(scrapers, num_threads=num_threads) as runner:
        runner_data = runner.parse_query(data) if search_type == "query" else runner.parse(search_type, data)

        for scraper, scraper_results in runner_data:
            for scraper_result in scraper_results:
                magnet = Magnet(scraper_result["magnet"])
                try:
                    info_hash = magnet.parse_info_hash()
                except InvalidMagnet:
                    continue
                if info_hash == "0" * 40:
                    continue

                magnet_result = results.get(info_hash)  # type: Result
                if magnet_result is None:
                    results[info_hash] = Result(scraper, scraper_result)
                else:
                    magnet_result.add_result(scraper, scraper_result)

    return [r.to_provider_result() for r in sorted(results.values(), key=Result.get_factor, reverse=True)]


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
