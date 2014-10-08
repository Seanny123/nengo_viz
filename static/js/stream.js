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

        // TODO: Make time control
    };
    ws.onclose = function() { 
        console.log("Connection is closed.");
    };
};