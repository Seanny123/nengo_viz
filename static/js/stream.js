// TODO: Figure out where the layout load is going to happen.

function stream() {
        console.log("create websocket...")
        //var ws = new WebSocket("ws://" + window.location.host + "/simulate?Id=123456789");
        var ws = new WebSocket("ws://localhost:8080/simulate?Id=123456789");
        console.log("WebSocket created.")
        ws.onopen = function() {
            console.log("Opening connection...")
            ws.send("Message to send");
            console.log("Opened connection.");
        };
        ws.onmessage = function (event) {
            console.log("Message parsing")
            d = $.parseJSON(event.data)
            $("#simulation #time").text(d.data.t.toFixed(3));
            var probe_data = [];
            $.each(d.data.probes, function(probe, x) {
                probe_data.push(probe + "=" + x);
            });
            $("#simulation #probes").text(probe_data.join("\n"));
            console.log("Message is received.");
            // TODO: Send the sliders that need to be passed and the current time
        };
        ws.onclose = function() { 
            console.log("Connection is closed.");
        };
};