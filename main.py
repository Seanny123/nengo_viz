"""Sean's hacky vizualizer proof of concept

Usage: python main.py [port=8080]
"""

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.autoreload
from tornado import gen

import numpy as np

import logging
import json
import os.path
import sys
import traceback
import webbrowser
import re
import keyword
import time
import multiprocessing
import datetime

import nengo_helper

import nengo
import viz
import nengo_viz.config
import nengo_viz.converter
import ipdb

import sys
#import pydevd

def get_milliseconds_diff(start, end):
    diff = start - end
    return (
            (diff.days * 24 * 60 * 60 + diff.seconds) * 1000
            + diff.microseconds / 1000.0
           )

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

class  MainHandler(tornado.web.RequestHandler):
    """Request handler for the main landing page."""
    @tornado.web.asynchronous
    def get(self):
        code = open("my_mult.py","r").read()
        model_container.gen_model(code)
        self.render('index.html')

class  ModelHandler(tornado.web.RequestHandler):
    """Giving the JSON"""
    def post(self):
        self.write(model_container.get_json())

class  ModelContainer(object):
    """an object to organize the model and it's manipulations"""
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
        self.sim_process = None
        self.clients = dict()
        # we have to do a bunch of weird stuff to make sure we can share
        # the simulator object between processes
        self.node_manager = multiprocessing.Manager()
        # this lock is mostly due to paranoia, I've yet to see evidence
        # where not using a lock would be a problem
        self.node_lock = multiprocessing.Lock()
        self.node_vals = self.node_manager.dict()
        self.message_count = 0
        # amount in milliseconds to wait between messages
        # if reduced beyond this point then D3.js has a hard time keeping up
        self.time_gap = 10

    def open(self, *args):
        """Callback for when the connection is opened."""
        self.id = self.get_argument("Id")
        self.stream.set_nodelay(True)
        self._is_closed = False

        dt = 0.001

        # Build the model and simulator in a seperate process
        simulator = nengo.Simulator(model_container.model, dt)
        # it's very useful to run this code without multiple processes when
        # debuggin
        #self._run_simulator(simulator)
        self.sim_process = multiprocessing.Process(target=self._run_simulator, args=(simulator,))
        self.sim_process.start()


    def _run_simulator(self, simulator):
        """Advances the simulator one step and sends results"""
        last_message_time = datetime.datetime.now()
        while not self._is_closed:
            # check to see if any of the inputs need to be over-ridden
            if(self.node_vals.items() != []):
                self.node_lock.acquire()
                # go through the network changing all of the original functions into overrideable ones
                for node_name, value in self.node_vals.items():
                    #print("overriding %s" %model_container.name_input_map[node_name])
                    new_node_val = self.node_vals.pop(node_name)
                    print("new_node_val={%s}" %new_node_val)
                    model_container.overrides[model_container.name_input_map[node_name]].set_value(new_node_val)
                self.node_lock.release()

            simulator.step()
            probes = dict()
            for probe in simulator.model.probes:
                probes[model_container.namefinder.name(probe)] = {"data":simulator.data[probe][-1].tolist()}
                # Because the probe dictionary of a simulator needs to be created every time it's called
                # and because probes accumulate data over time we have to delete the data that's been accumulated so far
                # or else the simple look-up on the previous line starts to take forever
                del simulator._probe_outputs[probe][:]

            data = {
                't': simulator.n_steps * simulator.model.dt,
                'probes': probes,
            }
            # Write the response out

            response = {"length":len(data), "data":data}
            # if the simulation is running too fast, tell it to sleep for a bit to let D3 catch up
            time_diff = get_milliseconds_diff(last_message_time, datetime.datetime.now())
            if(time_diff < self.time_gap):
                time.sleep((self.time_gap - time_diff)/1000)
            self.write_message(response)
            last_message_time = datetime.datetime.now()

    def on_message(self, message):
        """Receive the input information"""
        message = json.loads(message)
        self.node_lock.acquire()
        # add the new node value to the over-ride list
        self.node_vals[message['name']] = message['val']
        print("Result %s" %self.node_vals.items())
        self.message_count += 1
        self.node_lock.release()

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

# WTF. Why is this stuff outside of `if __name__ == '__main__':`
settings = {
    'static_path': os.path.join(os.path.dirname(__file__), 'static'),
    'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
    'debug': False,
}

# I want to rename graph.json to something that better describes what it's sending to the front end
application = Application([
    (r'/', MainHandler),
    (r'/simulate', SimulationHandler),
    (r'/graph.json', ModelHandler),
], **settings)

model_container = ModelContainer()

if __name__ == '__main__':
    port = int((sys.argv + [8082])[1])
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