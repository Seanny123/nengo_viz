// TODO: Figure out where the layout load is going to happen.

function stream(ws) {
    ws.onopen = function() {
        console.log("Opening connection...")
    };
    ws.onmessage = function tick(event) {
        var probeData = [];
        console.log("Message parsing");
        var d = $.parseJSON(event.data);
        // write out the time to show that something is being read
        $("#simulation #time").text(d.data.t.toFixed(3));
        probeDispatch.probeLoad(d.data.probes, d.data.t);
        console.log("Message is received.");

        // Does D3 dispatch wait for all the listeners to call back before continuing? I guess we'll have to try it out to know for sure!

        // TODO: Send the sliders that need to be passed
        // TODO: Make time control
    };
    ws.onclose = function() { 
        console.log("Connection is closed.");
    };
};