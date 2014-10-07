var probe_data = [];
$.each(d.data.probes, function(probe, x) {
    probe_data.push(probe + "=" + x);
});


/*
  slider.name = function(_) {
    if (!arguments.length) return name;
    name = _;
    return slider;
  };
*/

dispatch.on("statechange.pie", function(d) {
path.data(pie.value(function(g) { return d[g]; })(groups)).transition()
    .attrTween("d", function(d) {
      var interpolate = d3.interpolate(this._current, d);
      this._current = interpolate(0);
      return function(t) {
        return arc(interpolate(t));
      };
    });
});