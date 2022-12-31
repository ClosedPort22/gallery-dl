# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://2chen.moe/"""

from .common import Extractor, Message
from .. import text


class _2chenThreadExtractor(Extractor):
    """Extractor for 2chen threads"""
    category = "2chen"
    subcategory = "thread"
    directory_fmt = ("{category}", "{board}", "{thread} {title}")
    filename_fmt = "{time} {filename}.{extension}"
    archive_fmt = "{board}_{thread}_{hash}_{time}"
    pattern = r"(?:https?://)?2chen\.(?:moe|club)/([^/?#]+)/(\d+)"
    test = (
        ("https://2chen.moe/tv/496715", {
            "pattern": r"https://2chen\.su/assets/images/src/\w{40}\.\w+$",
            "count": ">= 179",
        }),
        ("https://2chen.club/tv/1", {
            "count": 5,
        }),
        # 404
        ("https://2chen.moe/jp/303786"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.root = text.root_from_url(match.group(0))
        self.board, self.thread = match.groups()

    def items(self):
        url = "{}/{}/{}".format(self.root, self.board, self.thread)
        page = self.request(url, encoding="utf-8", notfound="thread").text
        data = self.metadata(page)
        yield Message.Directory, data

        for post in self.posts(page):

            url = post["url"]
            if not url:
                continue
            if url[0] == "/":
                url = self.root + url
            post["url"] = url = url.partition("?")[0]

            post.update(data)
            post["time"] = text.parse_int(post["date"].timestamp())
            yield Message.Url, url, text.nameext_from_url(
                post["filename"], post)

    def metadata(self, page):
        board, pos = text.extract(page, 'class="board">/', '/<')
        title = text.extract(page, "<h3>", "</h3>", pos)[0]
        return {
            "board" : board,
            "thread": self.thread,
            "title" : text.unescape(title),
        }

    def posts(self, page):
        """Return iterable with relevant posts"""
        return map(self.parse, text.extract_iter(
            page, 'class="glass media', '</article>'))

    def parse(self, post):
        extr = text.extract_from(post)
        return {
            "name"    : text.unescape(extr("<span>", "</span>")),
            "date"    : text.parse_datetime(
                extr("<time", "<").partition(">")[2],
                "%d %b %Y (%a) %H:%M:%S"
            ),
            "no"      : extr('href="#p', '"'),
            "url"     : extr('</a><a href="', '"'),
            "filename": text.unescape(extr('download="', '"')),
            "hash"    : extr('data-hash="', '"'),
        }


class _2chenBoardExtractor(Extractor):
    """Extractor for 2chen boards"""
    category = "2chen"
    subcategory = "board"
    pattern = r"(?:https?://)?2chen\.(?:moe|club)/([^/?#]+)(?:/catalog|/?$)"
    test = (
        ("https://2chen.moe/co/", {
            "pattern": _2chenThreadExtractor.pattern
        }),
        ("https://2chen.moe/co"),
        ("https://2chen.club/tv"),
        ("https://2chen.moe/co/catalog"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.root = text.root_from_url(match.group(0))
        self.board = match.group(1)

    def items(self):
        url = "{}/{}/catalog".format(self.root, self.board)
        page = self.request(url, notfound="board").text
        data = {"_extractor": _2chenThreadExtractor}
        for thread in text.extract_iter(
                page, '<figure><a href="', '"'):
            yield Message.Queue, self.root + thread, data
