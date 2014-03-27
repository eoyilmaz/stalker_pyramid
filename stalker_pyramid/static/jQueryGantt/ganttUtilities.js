/*
 Copyright (c) 2012-2013 Open Lab
 Written by Roberto Bicchierai and Silvia Chelazzi http://roberto.open-lab.com
 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

$.fn.gridify = function (options) {
    this.options = {
        colResizeZoneWidth: 10
    };

    $.extend(this.options, options);
    $.gridify.init($(this), this.options);
    return this;
};

$.gridify = {
    init: function (elems, opt) {
        elems.each(function () {
            var table = $(this);

            //----------------------  header management start
            table.find("th.gdfColHeader.gdfResizable:not(.gdfied)").mouseover(function () {
                $(this).addClass("gdfColHeaderOver");

            }).bind("mouseout.gdf",function () {
                    $(this).removeClass("gdfColHeaderOver");
                    if (!$.gridify.columInResize) {
                        $("body").removeClass("gdfHResizing");
                    }

                }).bind("mousemove.gdf",function (e) {
                    if (!$.gridify.columInResize) {
                        var colHeader = $(this);
                        var mousePos = e.pageX - colHeader.offset().left;

                        if (colHeader.width() - mousePos < opt.colResizeZoneWidth) {
                            $("body").addClass("gdfHResizing");
                        } else {
                            $("body").removeClass("gdfHResizing");
                        }
                    }

                }).bind("mousedown.gdf",function (e) {
                    var colHeader = $(this);
                    var mousePos = e.pageX - colHeader.offset().left;
                    if (colHeader.width() - mousePos < opt.colResizeZoneWidth) {
                        $.gridify.columInResize = $(this);
                        //bind event for start resizing
                        //console.debug("start resizing");
                        $(document).bind("mousemove.gdf",function (e) {
                            //manage resizing
                            //console.debug(e.pageX - $.gridify.columInResize.offset().left)

                            var new_width = (e.pageX - $.gridify.columInResize.offset().left);
                            $.gridify.columInResize.width(new_width);

                            //bind mouse up on body to stop resizing
                        }).bind("mouseup.gdf", function () {
                                //console.debug("stop resizing");
                                $(this).unbind("mousemove.gdf").unbind("mouseup.gdf");
                                $("body").removeClass("gdfHResizing");
                                delete $.gridify.columInResize;
                            });
                    }
                }).addClass("gdfied unselectable").attr("unselectable", "true");


            //----------------------  cell management start wrapping
            table.find("td.gdfCell:not(.gdfied)").each(function () {
                var cell = $(this);
                if (cell.is(".gdfEditable")) {
                    var inp = $("<input type='text'>").addClass("gdfCellInput");
                    inp.val(cell.text());
                    cell.empty().append(inp);
                } else {
                    var wrp = $("<div>").addClass("gdfCellWrap");
                    wrp.html(cell.html());
                    cell.empty().append(wrp);
                }
            }).addClass("gdfied");

        });
    }
};

$.splittify = {
    init: function (where, first, second, perc) {
        perc = perc || 50;

        var splitter = $("<div>").addClass("splitterContainer");

        var firstBox = $("<div>").addClass("splitElement splitBox1");
        var splitterBar = $("<div>").addClass("splitElement vSplitBar").attr("unselectable", "on").html("|").css("padding-top", where.height() / 2 + "px");
        var secondBox = $("<div>").addClass("splitElement splitBox2");

        firstBox.append(first);
        secondBox.append(second);

        splitter.append(firstBox);
        splitter.append(secondBox);
        splitter.append(splitterBar);

        where.append(splitter);

        var w = where.innerWidth();
        var desired_width = w * perc / 100 - splitterBar.width();
        firstBox.width(desired_width).css({left: 0});

        splitterBar.css({left: desired_width});
        var splitterBar_width = splitterBar.width();
        // TODO: There is a 15px difference with the initial size and the first size on resize, monkey patching it
        //                   |
        //                   +-----------------------------------+
        //                                                       |
        //                                                       V
        secondBox.width(w - desired_width - splitterBar_width - 15).css({left:desired_width + splitterBar_width});

        splitterBar.bind("mousedown.gdf", function (e) {
            $.splittify.splitterBar = $(this);
            //bind event for start resizing
            //console.debug("start splitting");
            $("body").unselectable().bind("mousemove.gdf",function (e) {
                //manage resizing
                //console.debug(e.pageX - $.gridify.columInResize.offset().left)
                var sb = $.splittify.splitterBar;
                var pos = e.pageX - sb.parent().offset().left;
                var w = sb.parent().width();
                if (pos > 10 && pos < w - 20) {
                    sb.css({left: pos});
                    firstBox.width(pos);
                    secondBox.css({left: pos + splitterBar_width, width: w - pos - splitterBar_width});
                }

                //bind mouse up on body to stop resizing
            }).bind("mouseup.gdf", function () {
                    //console.debug("stop splitting");
                    $(this).unbind("mousemove.gdf").unbind("mouseup.gdf").clearUnselectable();
                    delete $.splittify.splitterBar;

                });
        });

        return {firstBox: firstBox, secondBox: secondBox, splitterBar: splitterBar};
    }
};

//<%------------------------------------------------------------------------  UTILITIES ---------------------------------------------------------------%>
function computeStart(start, timing_resolution) {
    // round to the given time interval
    timing_resolution = timing_resolution || 3600000; // 1 hour
    return (((start + timing_resolution * 0.5) / timing_resolution) >> 0 ) * timing_resolution;
}

function computeEnd(end, timing_resolution) {
    // round to the given time interval
    timing_resolution = timing_resolution || 3600000; // 1 hour
    return (((end + timing_resolution * 0.5) / timing_resolution) >> 0 ) * timing_resolution;
}

function computeEndByDuration(start, duration, timing_resolution) {
    timing_resolution = timing_resolution || 3600000; // 1 hour

    var end = start + duration - 1;
    return (((end + timing_resolution * 0.5) / timing_resolution) >> 0 ) * timing_resolution;
}

function incrementDateByWorkingDays(date, days) {
    var d = new Date(date);
    d.incrementDateByWorkingDays(days);
    return d.getTime();
}

function recomputeDuration(start, end) {
    //console.debug("recomputeDuration");
    //return new Date(start).distanceInWorkingDays(new Date(end));
    return new Date(end - start);
}


//This prototype is provided by the Mozilla foundation and
//is distributed under the MIT license.
//http://www.ibiblio.org/pub/Linux/LICENSES/mit.license

if (!Array.prototype.filter) {
    Array.prototype.filter = function (fun) {
        var len = this.length;
        if (typeof fun != "function")
            throw new TypeError();

        var res = new Array();
        var thisp = arguments[1];
        for (var i = 0; i < len; i++) {
            if (i in this) {
                var val = this[i]; // in case fun mutates this
                if (fun.call(thisp, val, i, this))
                    res.push(val);
            }
        }
        return res;
    };
}
