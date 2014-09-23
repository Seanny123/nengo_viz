import nengo
from nengo.utils.distributions import Uniform

model = nengo.Network(label='Two Neurons')
with model:
    neurons = nengo.Ensemble(2, dimensions=1,  # Representing a scalar
                             intercepts=Uniform(-.5, -.5),  # Set the intercepts at .5
                             max_rates=Uniform(100,100),  # Set the max firing rate at 100hz
                             encoders=[[1],[-1]])  # One 'on' and one 'off' neuron

    input = nengo.Node([0])

with model:
    nengo.Connection(input, neurons, synapse=0.01)

    nengo.Probe(input)  # The original input
    nengo.Probe(neurons, 'spikes')  # Raw spikes from each neuron
    nengo.Probe(neurons)