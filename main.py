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

clients = dict() # How do I put this inside SimulationHandler?

def isidentifier(s):
    if s in keyword.kwlist:
        return False
    return re.match(r'^[a-z_][a-z0-9_]*$', s, re.I) is not None

class MainHandler(tornado.web.RequestHandler):
    """Request handler for the main landing page."""
    @tornado.web.asynchronous
    def get(self):
        self.render('index.html')


class ModelHandler(object):

    @classmethod
    def get_model(cls, code, filename='error_msgs.txt'):
        c = compile(code.replace('\r\n', '\n'), filename, 'exec')
        locals = {}
        # apparently using globals causes this to break?
        exec c in locals
        return locals['model']

# Note that websockets aren't really used here, since it is assumed that only one browser will want to view the simulation at a time
class SimulationHandler(tornado.websocket.WebSocketHandler):
    """Request handler for streaming simulation data."""

    def open(self, *args):
        """Callback for when the connection is opened."""
        print("Connection opened")
        self.id = self.get_argument("Id")
        self.stream.set_nodelay(True)
        clients[self.id] = {"id": self.id, "object": self}
        self._is_closed = False
        print("done opening")

    # Websockets might be asynchronous by default
    #@tornado.web.asynchronous
    # the generator engine was selected since it has the most cross-platform compatibility
    #@gen.coroutine
    def on_message(self, message):
        """Asynchronously streams the simulation data."""
        # Read in the code and set the variables
        print("Message time")

        code = open("my_model.py","r").read()
        dt = 0.001

        # Build the model and simulator
        model = ModelHandler.get_model(code)
        simulator = nengo.Simulator(model, dt)

        """
        while(True):
            time.sleep(1)
            self.write_message(u"You said: " + message)
        """
        # At first connection, send a list of all the probes and the labels
        # of their associated nodes, so that the vizualizer has an idea of what
        # can be shown

        # Maintain an active connection, blocking only during each step
        while not self._is_closed:
            # In the basic streaming context, there is no need for generators, but in the context where we are dealing with other requests simultaneously, it starts to make a lot more sense that you would want to know exaclty how many steps to simulate and you would want to process them asynchronously
            #data = yield gen.Task(self._step, simulator)
            data = self._step(simulator)
            logging.debug('Connection (%d): %s', id(self), data)
            # Write the response out
            response = {"length":len(data), "data":data}
            print(type(response))
            self.write_message(response)
            #self.flush()

    def _step(self, simulator):#, callback):
        """Advances the simulator one step, and then invokes callback(data)."""
        simulator.step()
        probes = {}
        for probe in simulator.model.probes:
            probes[id(probe)] = list(simulator.data[probe][-1])
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

application = Application([
    (r'/', MainHandler),
    (r'/simulate', SimulationHandler),
], **settings)


if __name__ == '__main__':
    port = int((sys.argv + [8080])[1])
    application.listen(port)
    webbrowser.open_new_tab('http://localhost:%d/' % port)
    tornado.ioloop.IOLoop.instance().start()