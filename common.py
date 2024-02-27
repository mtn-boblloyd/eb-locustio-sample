from time import time
from locust import events
from contextlib import contextmanager, ContextDecorator

USERS = []
INVITE_CODES = []
PARTY_ROLES = [] #Host2 / Host3 / Solo / Joiner
REGION_PINGS = [50, 50, 50, 50, 50, 50]
RUNNING = {}
HAS_RUN = False
WAIT_SECONDS = 15
HEARTBEAT_REQUEST = "{\"requestId\":999,\"type\":\"PlayerSessionRpc.HeartbeatV1Request\",\"payload\":{}}"

@contextmanager
def _manual_report(name):
    start_time = time()
    try:
        yield
    except Exception as e:
        events.request.fire(
            request_type="pragma",
            name=name,
            response_time=(time() - start_time) * 1000,
            response_length=0,
            exception=e,
        )
        raise
    else:
        events.request.fire(
            request_type="pragma",
            name=name,
            response_time=(time() - start_time) * 1000,
            response_length=0,
            exception=None,
        )

def manual_report(name_or_func):
    if callable(name_or_func):
        # used as decorator without name argument specified
        return _manual_report(name_or_func.__name__)(name_or_func)
    else:
        return _manual_report(name_or_func)