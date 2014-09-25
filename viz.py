import struct

import nengo
import numpy as np

import time

# The idea behind Javaviz is that we needed the old vizualizer to work with the new software. To accomplish this we used the old software to talk to the old vizualizer, so we made the new software create nodes in the old software that just echos what is happening.

class View:
    def __init__(self, model, udp_port=56789, client='localhost',
                 default_labels={}, filename=None, realtime=False):
        self.default_labels = default_labels
        self.need_encoders = []
        self.overrides = {}
        self.override_last_time = {}
        self.block_time = 0.0
        self.should_reset = False
        self.should_stop = False
        self.realtime = realtime
        net.add(self.control_node)
        self.remote_objs = {}
        self.inputs = []
        self.probe_count = 0
        self.input_count = 0
        self.all_probes = []
        
        self.get_all_probes(model)
        self.process_network(net, model, names=[])

    def get_all_probes(self, network):
        for subnet in network.networks:
            self.get_all_probes(subnet)
            self.all_probes.extend(network.probes)
        self.all_probes.extend(network.probes)

    def get_name(self, names, obj, prefix):
        name = obj.label
        if name == None:
            name = self.default_labels.get(id(obj), None)
            if name is None:
                name = '%s_%d' % (obj.__class__.__name__, id(obj))

            # if the provided name has dots (indicating a hierarchy),
            # ignore them since that'll get filled in by the prefix
            if '.' in name:
                name = name.rsplit('.', 1)[1]

        if prefix != '':
            name = '%s.%s' % (prefix, name)

        counter = 2
        base = name
        while name in names:
            name = '%s (%d)' % (base, counter)
            counter += 1
        names.append(name)
        return name.replace('.', '>')

    # WTF does this do and how often is it executed? I'm just kind of confused how the simulator is incremented and the purpous of each network.
    def process_network(self, remote_net, network, names, prefix=''):
        semantic = []

        for network_ensemble in network.ensembles:
            for probe in self.all_probes:
                if probe.target is network_ensemble:
                    name = self.get_name(names, network_ensemble, prefix)

                    e = self.rpyc.modules.timeview.javaviz.ProbeNode(
                            self.value_receiver, name)

                    remote_net.add(e)
                    self.remote_objs[network_ensemble] = e

                    # Most of this code I don't think I can re-use, but what the hell does this do?
                    if network_ensemble.dimensions >= 8:
                        semantic.append(network_ensemble)
                    break

        for network_node in network.nodes:
                name = self.get_name(names, network_node, prefix)

                if network_node.size_in == 0: #If it's an input node
                    if network_node.size_out > 0: #And it has output
                        output = network_node.output

                        if callable(output): #If the output is callable, initialize it
                            output = output(0.0)

                        #Get the output dimensions
                        if isinstance(output, (int, float)):
                            output_dims = 1
                        elif isinstance(output, np.ndarray):
                            if output.shape == ():
                                output_dims = 1
                            else:
                                assert len(output.shape) == 1
                                output_dims = output.shape[0]
                        else:
                            output_dims = len(output)
                        # This new attribute is actually only used later in the network connections code
                        network_node._output_dims = output_dims

                        input = remote_net.make_input(name, tuple([0]*output_dims))
                        # Check if the what is ahead of the what?
                        network_node.output = OverrideFunction(self, network_node.output, 
                                    self.input_count)
                        self.control_node.register(self.input_count, input)
                        self.input_count += 1
                        self.remote_objs[network_node] = input
                        self.inputs.append(input)
                else:
                    for probe in self.all_probes:
                        if probe.target is network_node:
                            e = self.rpyc.modules.timeview.javaviz.ProbeNode(
                                    self.value_receiver, name)
                            remote_net.add(e)
                            self.remote_objs[network_node] = e
                            if network_node.size_out >= 8 and network_node.size_in == network_node.size_out:
                                semantic.append(network_node)
                            break

        for subnet in network.networks:
            name = self.get_name(names, subnet, prefix)
            self.process_network(remote_net, subnet, names, prefix=name)

        for obj in semantic:
            # do this after all the nodes and connections so that the
            # nodes and connections we create won't be mapped to remote
            self.add_semantic_override(obj, network)

        for probe in network.probes:

            probe_id = self.probe_count
            self.probe_count += 1

            if isinstance(probe.target, nengo.Ensemble) and probe.attr == 'decoded_output':
                obj = probe.target
                e = self.remote_objs[obj]
                e.add_probe(probe_id, obj.dimensions, 'X')
                with network:
                    def send(t, x, self=self, format='>Lf'+'f'*obj.dimensions,
                            id=probe_id):
                        msg = struct.pack(format, id, t, *x)
                        self.socket.sendto(msg, self.socket_target)

                    node = nengo.Node(send, size_in=obj.dimensions)
                    c = nengo.Connection(obj, node, synapse=None)

            elif isinstance(probe.target, nengo.Ensemble) and probe.attr == 'spikes':
                obj = probe.target
                e = self.remote_objs[obj]
                self.need_encoders.append(obj)
                e.add_spike_probe(probe_id, obj.n_neurons)
                with network:

                    def send(t, x, self=self, id=probe_id):
                        spikes = filter(lambda i: x[i] > 0.5, range(len(x)))
                        num_spikes = len(spikes)
                        format_string = '>LH'+'H'*num_spikes
                        msg = struct.pack(
                             format_string, id, num_spikes, *spikes)
                        self.socket.sendto(msg, self.socket_target)

                    node = nengo.Node(send, size_in=obj.n_neurons)
                    c = nengo.Connection(obj.neurons, node, synapse=None)
            elif isinstance(probe.target, nengo.Node) and probe.attr == 'output':
                obj = probe.target
                e = self.remote_objs[obj]
                if e in self.inputs:
                    # inputs are automatically probed
                    continue
                e.add_probe(probe_id, obj.size_out, 'X')
                with network:
                    def send(t, x, self=self, format='>Lf'+'f'*obj.size_out,
                            id=probe_id):
                        msg = struct.pack(format, id, t, *x)
                        self.socket.sendto(msg, self.socket_target)

                    node = nengo.Node(send, size_in=obj.size_out)
                    c = nengo.Connection(obj, node, synapse=None)

            else:
                print 'Unhandled probe', probe

    # WTF does this do?
    def add_semantic_override(self, obj, network):
        if isinstance(obj, nengo.Ensemble):
            dim = obj.dimensions
        elif isinstance(obj, nengo.Node):
            dim = obj.size_out
        remote = self.remote_objs[obj]
        self.control_node.register(self.input_count, remote)
        override_func = PassthroughOverrideFunction(self, self.input_count)
        with network:
            node = nengo.Node(override_func, size_in=dim, size_out=dim)
            nengo.Connection(obj, node, synapse=None)
            nengo.Connection(node, obj, synapse=0.05)

        self.input_count += 1



    # Don't I just send all the data from the probes and call it a day?
    def update_model(self, sim):
        """Grab data from the simulator needed for plotting."""

        for obj in self.need_encoders:
            remote = self.remote_objs[obj]
            encoders = sim.model.params[obj].encoders
            remote.set_encoders(obj.n_neurons, obj.dimensions,
                    tuple([float(x) for x in encoders.flatten()]))

# this replaces any callable nengo.Node's function with a function that:
# a) blocks if it gets ahead of the time the visualizer wants to show
# b) uses the slider value sent back from the visualizer instead of the
# output function, if that slider has been set
class OverrideFunction(object):
    def __init__(self, view, function, id):
        self.view = view
        self.function = function
        self.id = id
        self.view.overrides[id] = {}
    def check_reset(self):
        if self.view.should_reset:
            for k in self.view.overrides.keys():
                self.view.overrides[k] = {}
            self.view.override_last_time.clear()
            self.view.should_reset = False
            self.view.remote_view.sim_time = 0.0

            raise VisualizerResetException()

    def __call__(self, t):
        self.check_reset()
        while self.view.block_time < t:
            time.sleep(0.01)
            if self.view.should_stop:
                raise VisualizerExitException('JavaViz closed')
            self.check_reset()
        if callable(self.function):
            value = np.array(self.function(t), dtype='float')
        else:
            value = np.array(self.function, dtype='float')
        if len(value.shape) == 0:
            value.shape = (1,)
        for k,v in self.view.overrides.get(self.id, {}).items():
            value[k] = v
        return value

# This is meant for driving a Nengo node towards a particular value.
# The idea is to have a Node that takes input from a nengo Object and sends
# output back to that same object.  The "override" value comes from the
# javaviz visualizer.  If there is no override value (or if there hasn't
# been one for the last few time steps), then this node outputs a 0.
# Otherwise, it outputs the difference between the value it is receiving
# and the target value.  This should drive the nengo object it is connected
# to towards the override value.
class PassthroughOverrideFunction(object):
    def __init__(self, view, id):
        self.view = view
        self.id = id
        self.view.overrides[id] = {}
    def check_reset(self):
        if self.view.should_reset:
            for k in self.view.overrides.keys():
                self.view.overrides[k] = {}
            self.view.override_last_time.clear()
            self.view.should_reset = False
            self.view.remote_view.sim_time = 0.0

            raise VisualizerResetException()

    def __call__(self, t, x):
        self.check_reset()
        while self.view.block_time < t:
            time.sleep(0.01)
            if self.view.should_stop:
                raise VisualizerExitException('JavaViz closed')
            self.check_reset()
        value = np.array(x)
        last_time = self.view.override_last_time.get(self.id, None)
        if last_time is not None and t - last_time < 0.002:
            for k,v in self.view.overrides.get(self.id, {}).items():
                value[k] = v
        return 10*(value - x)


class VisualizerExitException(Exception):
    pass

class VisualizerResetException(Exception):
    pass