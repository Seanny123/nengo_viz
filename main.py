"""Sean's hacky vizualizer proof of concept

Usage: python main.py [port=8080]
"""

import tornado.ioloop
import tornado.web
from tornado import gen

import logging
import json
import os.path
import sys
import traceback
import webbrowser
import re
import keyword

import nengo_helper
import nengo

def isidentifier(s):
    if s in keyword.kwlist:
        return False
    return re.match(r'^[a-z_][a-z0-9_]*$', s, re.I) is not None

class ModelHandler(object):

    @classmethod
    def get_model(cls, code, filename='error_msgs.txt'):
        c = compile(code.replace('\r\n', '\n'), filename, 'exec')
        locals = {}
        # apparently using globals causes this to break?
        exec c in locals
        return locals['model']

class SimulationHandler(tornado.web.RequestHandler):
    """Request handler for streaming simulation data."""

    def prepare(self):
        """Callback for when the connection is opened."""
        self._is_closed = False

    @tornado.web.asynchronous
    @gen.engine
    def get(self):
        """Asynchronously streams the simulation data."""
        # Read in the code and set the variables
        code = open("my_model.py","r").read()
        dt = 0.001

        # Build the model and simulator
        model = ModelHandler.get_model(code)
        simulator = nengo.Simulator(model, dt)

        # At first connection, send a list of all the probes and the labels
        # of their associated nodes, so that the vizualizer has an idea of what
        # can be shown

        # Maintain an active connection, blocking only during each step
        while not self._is_closed:
            data = yield gen.Task(self._step, simulator)
            logging.debug('Connection (%d): %s', id(self), data)
            response = json.dumps(data)
            self.write('%d;%s;' % (len(response), response))
            self.flush()

    def _step(self, simulator, callback):
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
        tornado.ioloop.IOLoop.instance().add_callback(lambda: callback(data))

    def on_connection_close(self):
        """Callback for when the active connection is closed."""
        self._is_closed = True


class Application(tornado.web.Application):
    """Main application class for holding global server state."""

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
    (r'/', SimulationHandler),
], **settings)


if __name__ == '__main__':
    port = int((sys.argv + [8080])[1])
    application.listen(port)
    webbrowser.open_new_tab('http://localhost:%d/' % port)
    tornado.ioloop.IOLoop.instance().start()