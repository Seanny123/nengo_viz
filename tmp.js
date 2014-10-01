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