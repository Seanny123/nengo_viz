// TODO: Figure out where the layout load is going to happen.

function stream(ws) {
        //var probe_data = [];
        ws.onopen = function() {
            console.log("Opening connection...")
        };
        ws.onmessage = function tick(event) {
            console.log("Message parsing")
            d = $.parseJSON(event.data)
            $("#simulation #time").text(d.data.t.toFixed(3));
            $.each(d.data.probes, function(probe, x) {
                //probe_data.push(probe + "=" + x.data);
                myData.push(x.data); // this needs to handle multiple nodes
            });
            //$("#simulation #probes").text(probe_data.join("\n"));
            console.log("Message is received.");

            path
              .attr("d", line)
              .attr("transform", null)
            .transition()
              .duration(5)
              .ease("linear")
              .attr("transform", "translate(" + x(-1) + ",0)")
              .each("end", tick);

            myData.shift(); // Just for now

            // TODO: Send the sliders that need to be passed
            // TODO: Make time control
        };
        ws.onclose = function() { 
            console.log("Connection is closed.");
        };
};