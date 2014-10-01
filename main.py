"""Sean's hacky vizualizer proof of concept

Usage: python main.py [port=8080]
"""

import tornado.ioloop
import tornado.web
import tornado.websocket
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

import nengo_helper

import nengo
import viz
import nengo_viz.config
import nengo_viz.converter

clients = dict() # How do I put this inside SimulationHandler?

import sys

def isidentifier(s):
    if s in keyword.kwlist:
        return False
    return re.match(r'^[a-z_][a-z0-9_]*$', s, re.I) is not None

# There should really be a model object that holds the model and stuff

# A function that will return the result of the original function, unless it has ben overriden
class OverrideFunction:
    def __init__(self, original_function):
        self.original_function = original_function
        self.override_value = None
    # Not really used, since we create a new override function every time to change an input
    # Maybe we _should_ be using this?
    def set_value(self, value):    # override the value
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
        code = open("my_model.py","r").read()
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

    @classmethod
    def gen_model(self, code, filename='error_msgs.txt'):
        self.code = code
        c = compile(code.replace('\r\n', '\n'), filename, 'exec')
        locals = {}
        # apparently using globals causes this to break?
        exec c in locals

        self.model = locals['model']
        self.locals = locals

    @classmethod
    def get_json(self):
        conv = nengo_viz.converter.Converter(self.model, self.code.splitlines(), self.locals, nengo_viz.config.Config())
        return conv.to_json()

# Note that the broadcast function of websockets aren't really used here, since it is assumed that only one browser will want to view the simulation at a time
class SimulationHandler(tornado.websocket.WebSocketHandler):
    """Request handler for streaming simulation data."""

    def open(self, *args):
        """Callback for when the connection is opened."""
        print("Connection opened")
        self.id = self.get_argument("Id")
        self.stream.set_nodelay(True)
        clients[self.id] = {"id": self.id, "object": self}
        self._is_closed = False

        print("Message time")
        dt = 0.001

        # Build the model and simulator
        simulator = nengo.Simulator(model_container.model, dt)
        # Return the JSON
        self.write_message(model_container.get_json())
        # Maintain an active connection, blocking only during each step
        while not self._is_closed:
            # In the basic streaming context, there is no need for generators, but in the context where we are dealing with other requests simultaneously, it starts to make a lot more sense that you would want to know exaclty how many steps to simulate and you would want to process them asynchronously
            #data = yield gen.Task(self._step, simulator)
            data = self._step(simulator)
            time.sleep(0.05)
            #import ipdb; ipdb.set_trace()
            logging.debug('Connection (%d): %s', id(self), data)
            # Write the response out
            response = {"length":len(data), "data":data}
            print(type(response))
            self.write_message(response)
            #self.flush()


    # Websockets might be asynchronous by default
    #@tornado.web.asynchronous
    # the generator engine was selected since it has the most cross-platform compatibility
    #@gen.coroutine
    def on_message(self, message):
        """Receive the input information"""
        message = json.loads(message)


        # go through the network changing all of the original functions into overrideable ones
        my_overrides = {}
        for node in model_container.all_nodes:
            if node.size_in == 0 and node.size_out > 1:
                override = OverrideFunction(node.output)
                my_overrides[node] = override
                node.output = override


    def _step(self, simulator):#, callback):
        """Advances the simulator one step, and then invokes callback(data)."""
        simulator.step()
        probes = {}
        for probe in simulator.model.probes:
            # Might be able to simplify this code by using NameFinder 
            if(type(probe.target) == nengo.node.Node and hasattr(probe.target, 'label')):
                probes[id(probe)] = {"data":simulator.data[probe][-1].tolist(), "label":probe.target.label}
            elif(type(probe.target) == nengo.ensemble.Neurons and hasattr(probe.target.ensemble, 'label')):
                probes[id(probe)] = {"data":simulator.data[probe][-1].tolist(), "label":probe.target.ensemble.label}
            else:
                probes[id(probe)] = {"data":simulator.data[probe][-1].tolist()}

        data = {
            't': simulator.n_steps * simulator.model.dt,
            'probes': probes,
        }
        # Return control to the main IOLoop in order to process any other
        # pending requests, before re-entering the yield point in the coroutine
        #tornado.ioloop.IOLoop.instance().add_callback(lambda: callback(data))
        return data

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
    tornado.ioloop.IOLoop.instance().start()