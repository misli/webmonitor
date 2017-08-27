from itertools import chain
from random import shuffle
from signal import SIGINT, SIGTERM
from urllib.parse import urlsplit, urlunsplit

import aiohttp
import asyncio
import raven
import re
import traceback

import settings


class FakeDNSTCPConnector(aiohttp.connector.TCPConnector):

    def __init__(self, ip, **kwargs):
        self._ip = ip
        super(FakeDNSTCPConnector, self).__init__(**kwargs)

    async def _resolve_host(self, host, port):
        return [{'hostname': host, 'host': self._ip, 'port': port,
                 'family': self._family, 'proto': 0, 'flags': 0}]


class Check:
    def __init__(self, url, ip, code=200, regexp=None, **kwargs):
        self.url = url
        self.ip = ip
        self.code = code
        self.regexp = regexp and re.compile(regexp)
        self.kwargs = kwargs


class Monitor:
    def __init__(self, sentry):
        self.sentry = sentry
        self.checks = {}
        self.running_checks = 0
        for period, checks in settings.CHECKS.items():
            self.checks[period] = []
            for check in checks:
                try:
                    url, ips, params = check
                except:
                    url, ips = check
                    params = {}
                parts = urlsplit(url)
                for scheme in [parts.scheme] if parts.scheme else ['http', 'https']:
                    for ip in ips:
                        self.checks[period].append(Check(urlunsplit((scheme,)+parts[1:]), ip, **params))
            print('Configured {} checks with period {}s'.format(len(self.checks[period]), period))

    def run(self):
        self.stopping = False
        self.loop = asyncio.get_event_loop()
        self.loop.add_signal_handler(SIGINT, self.stop)
        self.loop.add_signal_handler(SIGTERM, self.stop)
        self.loop.run_until_complete(asyncio.wait([
            self.run_checks(period, checks) for period, checks in self.checks.items()
        ]))
        self.loop.run_until_complete(self.wait_for_running_checks())
        self.loop.close()

    def stop(self):
        self.stopping = True
        print('Stopping')

    async def wait_for_running_checks(self):
        while self.running_checks:
            print('Waiting for {} checks to finish'.format(self.running_checks))
            await asyncio.sleep(1)

    async def run_checks(self, period, checks):
        interval = period / len(checks)
        print('Interval between checks is {:.2}s'.format(interval))
        shuffle(checks)
        while not self.stopping:
            for check in checks:
                self.loop.create_task(self.check(check))
                await asyncio.sleep(interval)
                if self.stopping:
                    break

    async def check(self, check):
        self.running_checks += 1
        print(check.url, check.ip)
        try:
            connector = FakeDNSTCPConnector(check.ip, loop=self.loop)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(check.url, **check.kwargs) as response:
                    assert response.status == 200
                    if check.regexp:
                        content = await response.read()
                        assert check.regexp.search(content.decode())
        except:
            traceback.print_exc()
            sentry.captureException()
        finally:
            self.running_checks -= 1


if __name__ == '__main__':
    sentry = raven.Client(dsn=settings.SENTRY_DSN)
    try:
        monitor = Monitor(sentry)
        monitor.run()
    except:
        traceback.print_exc()
        sentry.captureException()
