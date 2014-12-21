nengo_viz
=========

Proof of concept for Nengo visualizer using Tornado.

To run it, install the requirements in `requirements.txt` and then run `python main.py`

Basically, `main.py` contains the server which initiates a session. The process
then forks into one "receiver" and one "runner", with the receiver getting
inputs via websockets and the runner running the model and sending the data
via websockets.

The main page is `templates/index.html` and the scripts are in the `static folder`
There are a lot of left-over files in here since I built this repository by just
taking everything from the `nengo_gui` repository.

In terms of JavaScript, what you need to pay attention to is the JavaScript in
`index.html` (which should really be extracted), `stream.js`, `gen_chart.js`
and `gen_slider.js`. The idea was to try and make these blue-prints so that other
developers could come along and create their own visualisations and inputs.