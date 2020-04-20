class Title(object):
    def __init__(self, title, titles=None):
        # type:(str, dict)->None
        self._title = title
        self._titles = titles or dict()

    @property
    def title(self):
        return self._title

    def __getattr__(self, item):
        return self._titles.get(item, self._title)

    def __str__(self):
        return self._title
