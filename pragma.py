import asyncio
import requests

class Pragma:
    def __init__(self, host = "http://127.0.0.1:11200"):
        self.host = host

    def call(self, uri, body, headers):
        url = f"{self.host}/{uri}"
        response = requests.post(url, json = body, headers = headers)
        if not response.ok:
            print(f"URI: {uri}")
            print(f"Body: {body}")
            print(f"Headers: {headers}")
            print(response.status_code)
            print(response.text)
            raise RuntimeError("Failed during connection to Pragma, see above messages for more information.")
        return response

    @asyncio.coroutine
    def _wait_call(self, timeout, url, body, headers):
        yield from asyncio.wait_for(requests.post(url, json = body, headers = headers), timeout=timeout)

    def async_call(self, timeout, uri, body, headers):
        url = f"{self.scheme}://{self.host}:{self.port}/{uri}"

        response_gen = self._wait_call(timeout, url, body, headers)
        response = next(response_gen)
        if not response.ok:
            print(response.status_code)
            print(response.text)
            raise RuntimeError("Could not connect to Pragma to authenticate the test user.  Check the response code above.")
        return response