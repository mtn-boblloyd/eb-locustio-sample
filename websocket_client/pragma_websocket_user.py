import ujson as json
import logging
import re
import time
import gevent
from locust import User
from locust_plugins import missing_extra
from common import WAIT_SECONDS, HEARTBEAT_REQUEST

try:
    import websocket
except ModuleNotFoundError:
    missing_extra("paho", "mqtt")


class PragmaWSUser(User):
    """
    A User that communicates with Pragma via a basic websocket connection
    """

    abstract = True
    is_disconnected = False
    last_received = None

    def connect(self, host: str, header=[], **kwargs):
        self.ws = websocket.create_connection(host, timeout=9000, header=header, **kwargs)
        self.ws_greenlet = gevent.spawn(self.receive_loop)

    def on_message(self, message_string):  # override this method in your subclass for custom handling

        response_time = 0  # unknown
        message = None
        try:
            message = json.loads(message_string)
        except Exception as e:
            logging.error(f'unable to parse response {message_string} e:{e}')
            messages = "" 
            #raise e

        name = self.get_name_from_json(message)

        message_length = 0
        if message is not None:
            message_length = len(message)

        self.environment.events.request.fire(
            request_type="WSR",
            name=name,
            response_time=response_time,
            response_length=message_length,
            exception=None,
            context=self.context(),
        )

    def receive_loop(self):
        while True:
            try:
                message = self.ws.recv()
                if (message is None) or (message == ""):
                    logging.error(f"no message received - still connected?{self.ws.connected}")
                    return
                #logging.debug(f"WSR: {message}")
                self.on_message(message)
            except Exception as e:
                logging.error(f'Exception in receive loop: {e}')
                raise


    def send(self, body, name=None, context={}):
        if not name:
                name = "No Name Provided"
        self.environment.events.request.fire(
            request_type="WSS",
            name=name,
            response_time=None,
            response_length=len(body),
            exception=None,
            context={**self.context(), **context},
        )
        #logging.debug(f"WSS: {body}")
        self.ws.send(body)

    def sleep_with_heartbeat(self, seconds):
        while seconds >= 0:
            gevent.sleep(min(WAIT_SECONDS, seconds))
            seconds -= WAIT_SECONDS
            self.send_heartbeat()

    def send_heartbeat(self):
        self.send(HEARTBEAT_REQUEST, "heartbeat")

    def get_name_from_message(self, message_string):
        message = json.loads(message_string)
        return self.get_name_from_json(message)

    def get_name_from_json(self, message):
        name = "unknown"

        if message is None:
            return "none"

        if "response" in message:
            name = message["response"]["type"]
        elif "notification" in message:
            name = message["notification"]["type"]
        elif "serviceError" in message:
            # name = message["serviceError"]["status"]
            name = message["serviceError"]["debugDetails"][0].split('\r\n')[0]
        else:
            logging.warn(f"missing name/type ${message}")
        return name
    
    def stringize_element(self, element, script_vars):
        str_element = json.dumps(element)
        for variable_name in script_vars:
            variable_value = script_vars.get(variable_name)
            str_element = str_element.replace("{{" + variable_name + "}}", variable_value)
        return str_element
    
    def listize_element(self, element, script_vars):
        element_list = element.items()
        strs = []
        for item in element_list:
            strs.append(self.parse_script_line(f"{item[0]}: {item[1]}", script_vars))
        return strs

    def wait_for_result(self, timeout):
        start_wait = time.time()
        signaled = self.notify_result.wait(timeout)
        if signaled and self.is_disconnected:
           logging.error(f'disconnected! ending')
        last_received = self.last_received
        self.last_received = 0
        waited = (time.time() - start_wait)
        self.notify_result.clear()
        if signaled:
            # tracking how long it took our coroutines to get to this, at a certain point the coroutines are the delay, not the server we're talking to
            event_delay = time.time() - last_received
            if last_received == 0:
                print('processing result after last_received when last received is 0')
            elif (event_delay > 5):
                print(f'waited for result signaled result: {event_delay}s')
        return waited

