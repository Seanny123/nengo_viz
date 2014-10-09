// Given an input, a dimension and a location, create the appropriate input
function genSlider(selector, name, label){
  d3.select(selector).call(d3.slider(name, ws).value(0).min(-5).max(5).orientation("vertical").axis(d3.svg.axis().ticks(3).orient("right")));
};