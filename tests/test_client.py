import pytest

from wdq.client import DisallowedByRobots, PoliteClient, RateLimiter


class FakeClock:
    def __init__(self):
        self.t = 100.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def test_rate_limiter_waits_between_calls_per_host():
    clock = FakeClock()
    rl = RateLimiter(1.0, clock=clock.now, sleep=clock.sleep)
    assert rl.wait("a.com") == 0  # first call never waits
    clock.t += 0.3
    assert rl.wait("a.com") == pytest.approx(0.7)
    assert rl.wait("b.com") == 0  # other host is independent
    clock.t += 5
    assert rl.wait("a.com") == 0


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


def make_client(robots_status, robots_text=""):
    client = PoliteClient("test-bot", min_interval=0)
    client.session.get = lambda url, timeout=None: FakeResponse(robots_status, robots_text)
    return client


def test_robots_disallow_blocks_url():
    client = make_client(200, "User-agent: *\nDisallow: /private/\n")
    client.check_allowed("https://example.com/public/page")  # no error
    with pytest.raises(DisallowedByRobots):
        client.check_allowed("https://example.com/private/page")


def test_missing_robots_means_allowed():
    client = make_client(404)
    client.check_allowed("https://example.com/anything")


def test_crawl_delay_raises_rate_limit():
    client = make_client(200, "User-agent: *\nCrawl-delay: 3\n")
    client.rate_limiter._sleep = lambda s: None
    client.throttle("https://example.com/")
    assert client.rate_limiter.min_interval == 3
