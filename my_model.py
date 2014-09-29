# # Nengo Example: A Single Neuron
# This demo shows you how to construct and manipulate a single leaky
# integrate-and-fire (LIF) neuron. The LIF neuron is a simple, standard
# neuron model, and here it resides inside a neural population, even though
# there is only one neuron.

import nengo
import nengo.utils.distributions as dists
import numpy as np

model = nengo.Network(label='Two Neurons')
with model:
    neurons = nengo.Ensemble(2, dimensions=1, # Represent a scalar
                            intercepts=dists.Uniform(-.5, -.5),  # Set intercept to 0.5
                            max_rates=dists.Uniform(100, 100),  # Set the maximum firing rate of the neuron to 100hz
                            encoders=[[1],[-1]], # Sets the neurons firing rate to increase for positive input
                            label = "A")
    sin_node = nengo.Node(lambda t: np.sin(8 * t), label="Shoop")
    # Connect and probe!
    # Connect the input signal to the neuron
    nengo.Connection(sin_node, neurons)

    pr_s = nengo.Probe(sin_node)  # The original input
    #nengo.Probe(neurons, 'voltage')  # The original input
    #nengo.Probe(neurons, 'spikes')  # The raw spikes from the neuron
    pr_e = nengo.Probe(neurons, synapse=0.01)  # The raw spikes from the neuron