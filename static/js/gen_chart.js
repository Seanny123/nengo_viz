// Given a location for inserting the chart and which probes to listen to generate a chart
// TODO: this function should return a D3 object so the outside code can manage it's location
function genChart(selector, probeLabelList, label, probeDispatch){

  console.log("creating chart");
  // The fact that we're copying the data to each chart feels weird.
  var n = 100;
  var chartData = Array.apply(null, Array(40)).map(Number.prototype.valueOf,0);
  var chartInputs = probeLabelList; //Probes to listen to

  // TODO: How to set these ranges according to the expected output? How did Javaviz do it?
  var margin = {top: 20, right: 20, bottom: 20, left: 40},
    width = 960 - margin.left - margin.right,
    height = 500 - margin.top - margin.bottom;

  // Domain is the minimum and maximum values to display on the graph
  // Range is the mount of SVG to cover
  // Get passed into the axes constructors
  // TODO: better names for these variables
  var xAxisScale = d3.scale.linear()
      .domain([0, n - 1])
      .range([0, width]);
   
  var yAxisScale = d3.scale.linear()
      .domain([-30, 30])
      .range([height, 0]);
   
  // gets a set of x and y co-ordinates from our data
  var line = d3.svg.line()
      // sets the x value to move forward with time
      .x(function(data, index) { return xAxisScale(index); })
      // sets the y value to just use the data y value
      .y(function(data, index) { return yAxisScale(data); });

  var svg = d3.select(selector).append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
  svg.append("defs").append("clipPath")
      .attr("id", "clip")
    .append("rect")
      .attr("width", width)
      .attr("height", height);

  // create the x and y axis

  svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + yAxisScale(0) + ")") // code for moving the x axis as it updates
      .call(d3.svg.axis().scale(xAxisScale).orient("bottom"));

  svg.append("g")
      .attr("class", "y axis")
      .call(d3.svg.axis().scale(yAxisScale).orient("left"));

  var path = svg.append("g")
      .attr("clip-path", "url(#clip)") // limit where the line can be drawn
    .append("path")
      .datum(chartData) // chartData is the data we're going to plot
      .attr("class", "line")
      .attr("d", line); // This is to help draw the sgv path



  probeDispatch.on(("probeLoad."+label), function(probeData, simTime) {
    // Filter until you have only the desired data
    // TODO: Make this work for multiple probes

    // Loop through each of the inputs you want to plot
    chartInputs.forEach(function(input) {
          // Remove the old data
        chartData.shift();
        chartData.push(probeData[input].data[0]);
    });

    // Then update the path
    path
      .attr("d", line)
      .attr("transform", null)
    .transition()
      .duration(0.1) // is it the duration of the transition?
      .ease("linear") // this is just to say that the speed of the line should be constant
      .attr("transform", "translate(" + xAxisScale(-1) + ",0)");
  });

}