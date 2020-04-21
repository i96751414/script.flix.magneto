from flix.provider import Provider


class MagnetoProvider(Provider):
    def search(self, query):
        return []

    def search_movie(self, tmdb_id, title, titles, year=None):
        return []

    def search_episode(self, tmdb_id, show_title, season_number, episode_number, titles):
        return []

    def resolve(self, magnet):
        return "plugin://plugin.video.torrest/play_magnet/{}".format(magnet)
