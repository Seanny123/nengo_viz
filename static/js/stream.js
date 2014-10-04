// TODO: Figure out where the layout load is going to happen.

function stream(ws) {

        ws.onopen = function() {
            console.log("Opening connection...")
        };
        ws.onmessage = function tick(event) {
            console.log("Message parsing")
            d = $.parseJSON(event.data)
            $("#simulation #time").text(d.data.t.toFixed(3));
            $.each(d.data.probes, function(probe, x) {
                probeData.push(x.data); // this needs to handle multiple nodes
            });
            console.log("Message is received.");

            path
              .attr("d", line)
              .attr("transform", null)
            .transition()
              .duration(1)
              .ease("linear")
              .attr("transform", "translate(" + x(-1) + ",0)")
              .each("end", tick);

            // Does D3 dispatch wait for all the listeners to call back before continuing? I guess we'll have to try it out to know for sure!

            probeData.shift(); // Delete the data

            // TODO: Send the sliders that need to be passed
            // TODO: Make time control
        };
        ws.onclose = function() { 
            console.log("Connection is closed.");
        };
};