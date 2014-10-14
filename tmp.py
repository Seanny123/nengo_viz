probes = {}
for probe in sim.model.probes:
    probes[probe.attr] = list(sim.data[probe][-1])
data = {
    't': sim.n_steps * sim.model.dt,
    'probes': probes,
}

code = open("my_model.py","r").read(); c = compile(code.replace('\r\n', '\n'), 'error_m.txt', 'exec'); locals = {}; globals = {}; exec c in locals

import nengo
import nengo.utils.distributions as dists
import numpy

pr = ""

model = nengo.Network(label='Two Neurons')
with model:
    neurons = nengo.Ensemble(2, dimensions=1, # Represent a scalar
                            intercepts=dists.Uniform(-.5, -.5),  # Set intercept to 0.5
                            max_rates=dists.Uniform(100, 100),  # Set the maximum firing rate of the neuron to 100hz
                            encoders=[[1],[-1]], # Sets the neurons firing rate to increase for positive input
                            label = "A")
    sin_node = nengo.Node(lambda t: numpy.sin(8 * t))
    # Connect and probe!
    # Connect the input signal to the neuron
    nengo.Connection(sin_node, neurons)

    nengo.Probe(sin_node)  # The original input
    nengo.Probe(neurons, 'voltage')  # The original input
    nengo.Probe(neurons, 'spikes')  # The raw spikes from the neuron
    nengo.Probe(neurons, synapse=0.01)  # The raw spikes from the neuron # No label because testing!

sim = nengo.Simulator(model, 0.001)
sim.step()

import multiprocessing

class Dog():
    def __init__(self, name = "joe"):
        self.name = name
    def bark(self):
        print("woof")

mg = multiprocessing.Manager()
dt = dict()
lp = mg.list()
lp.append(dt)
print(lp)
dt["a"] = 1
dt["b"] = 2
lp[0] = dt
print(lp)
dt = dict()
lab = Dog("carl")
print(lab)
pup = Dog("steve")
print(pup)
dt[lab] = 1
dt[pup] = 2
lp[0] = dt
print(lp)