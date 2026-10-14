"""A fake YouTube Data API client.

Enough of the fluent surface to exercise ytmla.localize and ytmla.upload for real:
the fake actually APPLIES updates, so a re-read returns new state. That matters --
the bug this guards against is the API accepting a call that does not stick.
"""


class _Req:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class _Videos:
    def __init__(self, state, calls, fail_update=None):
        self.s, self.calls, self.fail_update = state, calls, fail_update

    def list(self, part=None, id=None):
        self.calls.append(("list", part, id))
        vid = id if isinstance(id, str) else (id[0] if id else None)
        if vid not in self.s:
            return _Req(lambda: {"items": []})
        return _Req(lambda: {"items": [self.s[vid].copy()]})

    def update(self, part=None, body=None):
        self.calls.append(("update", part, body))

        def go():
            vid = body["id"]
            if self.fail_update:
                # simulate the API accepting the call but not persisting the change
                return {"id": vid}
            item = self.s.setdefault(vid, {})
            sn = item.setdefault("snippet", {})
            sn.update({k: v for k, v in body.get("snippet", {}).items()})
            item["localizations"] = {k: dict(v) for k, v in (body.get("localizations") or {}).items()}
            return {"id": vid}

        return _Req(go)


class _Channels:
    def __init__(self, state, calls):
        self.s, self.calls = state, calls

    def list(self, part=None, mine=None):
        self.calls.append(("channels.list", part))

        def go():
            return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU"}},
                               "snippet": {"title": "fake"}, "status": {"longUploadsStatus": "allowed"}}]}

        return _Req(go)


class _Insert:
    def __init__(self, state, calls, vid="NEWVID00001"):
        self.s, self.calls, self.vid = state, calls, vid

    def next_chunk(self):
        self.calls.append(("insert",))
        self.s[self.vid] = {"snippet": {"title": "t", "description": "d"},
                            "status": {"privacyStatus": "private"}}
        return None, {"id": self.vid}


class FakeYouTube:
    """`videos()` is a method but also needs `.insert`, mirroring googleapiclient."""
    def __init__(self, videos=None, fail_update=False):
        self.state = videos or {}
        self.calls = []
        self._v = _Videos(self.state, self.calls, fail_update)
        self._c = _Channels(self.state, self.calls)

    def videos(self):
        outer = self

        class _V:
            def list(self, **kw):
                return outer._v.list(**kw)

            def update(self, **kw):
                return outer._v.update(**kw)

            def insert(self, **kw):
                return _Insert(outer.state, outer.calls)

        return _V()

    def channels(self):
        return self._c
