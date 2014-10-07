// Given an input, a dimension and a location, create the appropriate input
function genSlider(selector, name, label){
  console.log("makin' a slider")
  d3.select(selector).call(d3.slider(name, ws).value(0).min(-1).max(1).orientation("vertical"));
};