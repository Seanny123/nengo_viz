// Given a location for inserting the chart and which probes to listen to generate a chart
// So, will these variables still exists after the function is done?
// I GUESS WE'LL HAVE TO TRY AND FIND OUT
function gen_chart(selector, probeLableList, label){

// Domain is the minimum and maximum values to display on the graph
// Range is the mount of SVG to cover
// Get passed into the axes constructors
var x = d3.scale.linear()
    .domain([0, n - 1])
    .range([0, width]);
 
var y = d3.scale.linear()
    .domain([-1, 1])
    .range([height, 0]);
 
// gets a set of x and y co-ordinates from our data
var line = d3.svg.line()
    // sets the x value to move forward with time
    .x(function(data, index) { return x(index); })
    // sets the y value to just use the data y value
    .y(function(data, index) { return y(index); });


var svg = d3.select("body").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
  .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
 
svg.append("defs").append("clipPath")
    .attr("id", "clip")
  .append("rect")
    .attr("width", width)
    .attr("height", height);

// code for moving the x axis as it updates
svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + y(0) + ")")
    .call(d3.svg.axis().scale(x).orient("bottom"));

// define the y axis
svg.append("g")
    .attr("class", "y axis")
    .call(d3.svg.axis().scale(y).orient("left"));

var path = svg.append("g")
    .attr("clip-path", "url(#clip)") // limit where the line can be drawn
  .append("path")
    .datum(myData)
    .attr("class", "line")
    .attr("d", line); // This is to help draw the sgv path



};