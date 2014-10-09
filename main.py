"""Sean's hacky vizualizer proof of concept

Usage: python main.py [port=8080]
"""

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.autoreload
from tornado import gen

import logging
import json
import os.path
import sys
import traceback
import webbrowser
import re
import keyword
import time
import thread
import multiprocessing
import multiprocessing.managers

import nengo_helper

import nengo
import viz
import nengo_viz.config
import nengo_viz.converter
import ipdb

import sys

def isidentifier(s):
    if s in keyword.kwlist:
        return False
    return re.match(r'^[a-z_][a-z0-9_]*$', s, re.I) is not None

# A function that will return the result of the original function, unless it has ben overriden
class OverrideFunction:
    def __init__(self, original_function):
        self.original_function = original_function
        self.override_value = None
    def set_value(self, value):
        self.override_value = value
    def __call__(self, t):
        if self.override_value is None:
            return self.original_function(t)
        else:
            return self.override_value

class MainHandler(tornado.web.RequestHandler):
    """Request handler for the main landing page."""
    @tornado.web.asynchronous
    def get(self):
        code = open("my_mult.py","r").read()
        model_container.gen_model(code)
        self.render('index.html')

class ModelHandler(tornado.web.RequestHandler):
    """Giving the JSON"""
    def post(self):
        self.write(model_container.get_json())

class ModelContainer(object):

    def __init__(self):
        self.model = None
        self.locals = None
        self.code = None
        self.namefinder = None
        self.conv = None
        self.overrides = dict()
        self.name_input_map = dict()

    def gen_model(self, code, filename='error_msgs.txt'):
        print("Making the model")
        self.code = code
        c = compile(code.replace('\r\n', '\n'), filename, 'exec')
        locals = {}
        # apparently using globals causes this to break?
        exec c in locals

        self.model = locals['model']
        self.locals = locals
        self.conv = nengo_viz.converter.Converter(self.model, self.code.splitlines(), self.locals, nengo_viz.config.Config())
        self.namefinder = self.conv.namefinder
        
        # Make all the input nodes overrideable
        for node in self.model.all_nodes:
            if node.size_in == 0 and node.size_out >= 1:
                #print("Overriding!")
                override = OverrideFunction(node.output)
                self.overrides[node] = override
                self.name_input_map[self.namefinder.known_name[id(node)]] = node
                node.output = override

    def get_json(self):
        # Why are we sending the known_name dict again?
        return json.dumps([self.conv.data_dump(), self.conv.namefinder.known_name])

    def get_overrides(self):
        "Accessor for multiprocessing purposes, not sure if necessary"
        return self.overrides

# Note that the broadcast function of websockets aren't really used here, since it is assumed that only one browser will want to view the simulation at a time
class SimulationHandler(tornado.websocket.WebSocketHandler):
    """Request handler for streaming simulation data."""

    def __init__(self, *args, **kwargs):
        super(SimulationHandler, self).__init__(*args, **kwargs)
        self.clients = dict()
        self.message_count = 0
        #self.manager = multiprocessing.managers.BaseManager()
        #self.manager.register("nengo.Simulator", nengo.Simulator, exposed=["probes"])
        #self.manager.register("ModelContainer", nengo.Simulator, exposed=["get_overrides"])

    def open(self, *args):
        """Callback for when the connection is opened."""
        self.id = self.get_argument("Id")
        self.stream.set_nodelay(True)
        #self.clients[self.id] = {"id": self.id, "object": self} # Not necessary?
        self._is_closed = False

        dt = 0.001

        # Build the model and simulator
        # Maintain an active connection, blocking only during each step # This is going to open a new simulation for every new connection. Is that the behaviour we want? # I think we might need to use multithreading here # Goddamn producer consumer problem
        #simulator = nengo.Simulator(model_container.model, dt)
        #sim_thread = threading.Thread(target=self._run_simulator, args=(simulator,))
        #sim_thread.daemon = True #So that I can terminate the program easily
        #sim_thread.start()


    def _run_simulator(self, simulator):
        """Advances the simulator one step, and then invokes callback(data)."""
        while not self._is_closed:
            #self.simulator_lock.acquire()
            simulator.step()
            #self.simulator_lock.release()
            probes = dict()
            for probe in simulator.model.probes:
                probes[model_container.namefinder.name(probe)] = {"data":simulator.data[probe][-1].tolist()}

            data = {
                't': simulator.n_steps * simulator.model.dt,
                'probes': probes,
            }
            #time.sleep(0.1) # slow it down for debugging
            #logging.debug('Connection (%d): %s', id(self), data)
            # Write the response out
            response = {"length":len(data), "data":data}
            #print(type(response)) #It's a dict type but it's still not being sent as JSON.
            print("Sending message %i" %self.message_count)
            self.write_message(response)
            self.message_count += 1

    def on_message(self, message):
        """Receive the input information"""
        message = json.loads(message)
        print("Received %s" %message)

        # go through the network changing all of the original functions into overrideable ones
        my_overrides = {}
        #self.simulator_lock.acquire()
        # look up the node name in the input dict and assign it the value #TODO: test for two-dimensional values
        model_container.overrides[model_container.name_input_map[message['name']]].set_value(message['val'])
        #self.simulator_lock.release()

    def on_close(self):
        """Callback for when the active connection is closed."""
        self._is_closed = True

class Application(tornado.web.Application):
    # Main application class for holding global server state.

    def __init__(self, *args, **kwargs):
        # Set up globally accessible data-structures / etc in here!
        # They can be accessed in the request via self.application.

        # Set up logging
        level = logging.DEBUG if kwargs['debug'] else logging.WARNING
        logging.root.setLevel(level)

        super(Application, self).__init__(*args, **kwargs)


settings = {
    'static_path': os.path.join(os.path.dirname(__file__), 'static'),
    'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
    'debug': True,
}

# I want to rename graph.json to something that better describes what it's sending to the front end
application = Application([
    (r'/', MainHandler),
    (r'/simulate', SimulationHandler),
    (r'/graph.json', ModelHandler),
], **settings)

model_container = ModelContainer()


if __name__ == '__main__':
    port = int((sys.argv + [8080])[1])
    application.listen(port)
    webbrowser.open_new_tab('http://localhost:%d/' % port)
    # For debugging purposes reload Tornado whenever one of the static (Javascript, CSS, HTML) are loaded
    tornado.autoreload.start()
    for dir, _, files in os.walk('static'):
        [tornado.autoreload.watch(dir + '/' + f) for f in files if not f.startswith('.')]
    for dir, _, files in os.walk('templates'):
        [tornado.autoreload.watch(dir + '/' + f) for f in files if not f.startswith('.')]
    # Start this puppy up!
    tornado.ioloop.IOLoop.instance().start()