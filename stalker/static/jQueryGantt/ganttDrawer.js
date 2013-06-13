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
function GanttDrawer(zoom, startmillis, endMillis, master, minGanttSize) {
    this.master = master; // is the a GantEditor instance
    this.element; // is the jquery element containing gantt
    this.highlightBar;
    this.zoom = zoom;
    this.minGanttSize = minGanttSize;
    this.includeToday = true; //when true today is always visible. If false boundaries comes from tasks periods
    
    this.computedTableWidth = null;

    this.zoomLevels = ['h', "d", "w", "m", "q", "s", "y"];
    //this.zoomLevels = ["w","m","q","s","y"];
    
//    console.debug('GanttDrawer.startmillis : ', startmillis);
//    console.debug('GanttDrawer.endMillis   : ', endMillis);

    this.element = this.create(zoom, startmillis, endMillis);

}

GanttDrawer.prototype.zoomGantt = function (isPlus) {
    var curLevel = this.zoom;
    var pos = this.zoomLevels.indexOf(curLevel + "");

    var newPos = pos;
    if (isPlus) {
        newPos = pos <= 0 ? 0 : pos - 1;
    } else {
        newPos = pos >= this.zoomLevels.length - 1 ? this.zoomLevels.length - 1 : pos + 1;
    }
    if (newPos != pos) {
        curLevel = this.zoomLevels[newPos];
        this.zoom = curLevel;
        this.refreshGantt();
    }

    // refresh links
    // TODO: do not use gotoLink, replace it with the new script
    require(['stalker/gotoLink'], function (gotoLink) {
        gotoLink();
    });

};


GanttDrawer.prototype.create = function (zoom, originalStartMillis, originalEndMillis) {
    //console.debug("Gantt.create " + new Date(originalStartMillis) + " - " + new Date(originalEndMillis));

    var self = this;
    
    // reset time
    var temp_start = new Date(originalStartMillis);
    var temp_end = new Date(originalEndMillis);
    temp_start.setHours(0, 0, 0, 0);
    temp_end.setHours(23, 59, 59, 999);

    originalStartMillis = temp_start.getTime();
    originalEndMillis = temp_end.getTime();


    function getPeriod(zoomLevel, stMil, endMillis) {
        var start = new Date(stMil);
        var end = new Date(endMillis);


        start.setHours(0, 0, 0, 0);
        end.setHours(23, 59, 59, 999);
        //reset hours
        if (zoomLevel == "d") {

        } else if (zoomLevel == "w") {
            //reset day of week
            start.setFirstDayOfThisWeek();
            end.setFirstDayOfThisWeek();
            end.setDate(end.getDate() + 6);
        } else if (zoomLevel == "m") {
            //reset day of month
            start.setDate(1);
            end.setDate(1);
            end.setMonth(end.getMonth() + 1);
            end.setDate(end.getDate() - 1);
        } else if (zoomLevel == "q") {
            //reset to quarter
            start.setDate(1);
            start.setMonth(Math.floor(start.getMonth() / 3) * 3);
            end.setDate(1);
            end.setMonth(Math.floor(end.getMonth() / 3) * 3 + 3);
            end.setDate(end.getDate() - 1);
        } else if (zoomLevel == "s") {
            //reset to semester
            start.setDate(1);
            start.setMonth(Math.floor(start.getMonth() / 6) * 6);
            end.setDate(1);
            end.setMonth(Math.floor(end.getMonth() / 6) * 6 + 6);
            end.setDate(end.getDate() - 1);
        } else if (zoomLevel == "y") {
            //reset to year - > gen
            start.setDate(1);
            start.setMonth(0);

            end.setDate(1);
            end.setMonth(12);
            end.setDate(end.getDate() - 1);
        }
        return {start: start.getTime(), end: end.getTime()};
    }

    function createHeadCell(lbl, span, additionalClass) {
        var th = $("<th>").html(lbl).attr("colSpan", span);
        if (additionalClass)
            th.addClass(additionalClass);
        return th;
    }

    function createBodyCell(span, isEnd, additionalClass) {
        var ret = $("<td>").html("&nbsp;").attr("colSpan", span).addClass("ganttBodyCell");
        if (isEnd)
            ret.addClass("end");
        if (additionalClass)
            ret.addClass(additionalClass);
        return ret;
    }

    function createGantt(zoom, startPeriod, endPeriod) {
//        console.debug('startPeriod : ', startPeriod);
//        console.debug('endPeriod   : ', endPeriod);
        var tr1 = $("<tr>").addClass("ganttHead1");
        var tr2 = $("<tr>").addClass("ganttHead2");
        var trBody = $("<tr>").addClass("ganttBody");

        function iterate(renderFunction1, renderFunction2) {
            var start = new Date(startPeriod);
            //loop for header1
            while (start.getTime() <= endPeriod) {
                renderFunction1(start);
            }

            //loop for header2
            start = new Date(startPeriod);
            while (start.getTime() <= endPeriod) {
                renderFunction2(start);
            }
        }

        //this is computed by hand in order to optimize cell size
        var computedTableWidth;


        if (zoom == "y") {
            // year
            computedTableWidth = Math.floor(((endPeriod - startPeriod) / (3600000 * 24 * 180)) * 100); //180gg = 1 sem = 100px
            iterate(function (date) {
                tr1.append(createHeadCell(date.format("yyyy"), 2));
                date.setFullYear(date.getFullYear() + 1);
            }, function (date) {
                var sem = (Math.floor(date.getMonth() / 6) + 1);
                //tr2.append(createHeadCell(GanttMaster.messages["GANTT_SEMESTER_SHORT"] + sem, 1));
                tr2.append(createHeadCell('S' + sem, 1));
                trBody.append(createBodyCell(1, sem == 2));
                date.setMonth(date.getMonth() + 6);
            });

        } else if (zoom == "s") {
            //semester
            computedTableWidth = Math.floor(((endPeriod - startPeriod) / (3600000 * 24 * 90)) * 100); //90gg = 1 quarter = 100px
            iterate(function (date) {
                var end = new Date(date.getTime());
                end.setMonth(end.getMonth() + 6);
                end.setDate(end.getDate() - 1);
                tr1.append(createHeadCell(date.format("MMM") + " - " + end.format("MMM yyyy"), 2));
                date.setMonth(date.getMonth() + 6);
            }, function (date) {
                var quarter = ( Math.floor(date.getMonth() / 3) + 1);
                //tr2.append(createHeadCell(GanttMaster.messages["GANT_QUARTER_SHORT"] + quarter, 1));
                tr2.append(createHeadCell('Q' + quarter, 1));
                trBody.append(createBodyCell(1, quarter % 2 == 0));
                date.setMonth(date.getMonth() + 3);
            });

        } else if (zoom == "q") {
            //quarter
            computedTableWidth = Math.floor(((endPeriod - startPeriod) / (3600000 * 24 * 30)) * 300); //1 month= 300px
            iterate(function (date) {
                var end = new Date(date.getTime());
                end.setMonth(end.getMonth() + 3);
                end.setDate(end.getDate() - 1);
                tr1.append(createHeadCell(date.format("MMM") + " - " + end.format("MMM yyyy"), 3));
                date.setMonth(date.getMonth() + 3);
            }, function (date) {
                var lbl = date.format("MMM");
                tr2.append(createHeadCell(lbl, 1));
                trBody.append(createBodyCell(1, date.getMonth() % 3 == 2));
                date.setMonth(date.getMonth() + 1);
            });
        } else if (zoom == "m") {
            //month
            computedTableWidth = Math.floor(((endPeriod - startPeriod) / (3600000 * 24 * 1)) * 20); //1 day= 20px
            iterate(function (date) {
                var sm = date.getTime();
                date.setMonth(date.getMonth() + 1);
                var daysInMonth = parseInt((date.getTime() - sm) / (3600000 * 24));
                tr1.append(createHeadCell(new Date(sm).format("MMMM yyyy"), daysInMonth)); //spans mumber of dayn in the month
            }, function (date) {
                //tr2.append(createHeadCell(date.format("d"), 1, isHoliday(date) ? "holyH" : null));
                tr2.append(createHeadCell(date.format("d"), 1, date.getDay() == 0 ? "holyH" : null));
                var nd = new Date(date.getTime());
                nd.setDate(date.getDate() + 1);
                //trBody.append(createBodyCell(1, nd.getDate() == 1, isHoliday(date) ? "holy" : null));
                trBody.append(createBodyCell(1, nd.getDate() == 1, date.getDay() == 0 ? "holy" : null));
                date.setDate(date.getDate() + 1);
            });
        } else if (zoom == "w") {
            //week
            computedTableWidth = Math.floor(((endPeriod - startPeriod) / (3600000 * 24)) * 30); //1 day= 30px
            iterate(function (date) {
                var end = new Date(date.getTime());
                end.setDate(end.getDate() + 6);
                tr1.append(createHeadCell(date.format("MMM d") + " - " + end.format("MMM d'yy"), 7));
                date.setDate(date.getDate() + 7);
            }, function (date) {
                //tr2.append(createHeadCell(date.format("EEEE").substr(0, 1), 1, isHoliday(date) ? "holyH" : null));
                //trBody.append(createBodyCell(1, date.getDay() % 7 == (self.master.firstDayOfWeek + 6) % 7, isHoliday(date) ? "holy" : null));
                tr2.append(createHeadCell(date.format("EEEE").substr(0, 1), 1, date.getDay() == 0 ? "holyH" : null));
                trBody.append(createBodyCell(1, date.getDay() % 7 == (self.master.firstDayOfWeek + 6) % 7, date.getDay() == 0 ? "holy" : null));
                date.setDate(date.getDate() + 1);
            });
        } else if (zoom == "d") {
            //days
            computedTableWidth = Math.floor(((endPeriod - startPeriod) / (3600000 * 24)) * 200); //1 day= 200px
            iterate(function (date) {
                //tr1.append(createHeadCell(date.format("EEEE d MMMM yyyy"), 4, isHoliday(date) ? "holyH" : null));
                tr1.append(createHeadCell(date.format("EEEE d MMMM yyyy"), 4, date.getDay() == 0 ? "holyH" : null));
                date.setDate(date.getDate() + 1);
            }, function (date) {
                //tr2.append(createHeadCell(date.format("HH"), 1, isHoliday(date) ? "holyH" : null));
                //trBody.append(createBodyCell(1, date.getHours() > 18, isHoliday(date) ? "holy" : null));
                tr2.append(createHeadCell(date.format("HH"), 1, date.getDay() == 0 ? "holyH" : null));
                trBody.append(createBodyCell(1, date.getHours() > 18, date.getDay() == 0 ? "holy" : null));
                date.setHours(date.getHours() + 6);
            });
        } else if (zoom == "h") {
            // hours
            computedTableWidth = Math.floor(((endPeriod - startPeriod ) / 3600000) * 40); // 1 hour= 50px
            iterate(function (date) {
                //tr1.append(createHeadCell(date.format('EEE d MMMM yyyy'), 24, isHoliday(date) ? 'holyH': null));
                tr1.append(createHeadCell(date.format('EEE d MMMM yyyy'), 24, date.getDay() == 0 ? 'holyH' : null));
                date.setDate(date.getDate() + 1);
            }, function (date) {
                //tr2.append(createHeadCell(date.format('HH'), 1, isHoliday(date) ? 'holyH': null));
                //trBody.append(createBodyCell(1, date.getHours() > 18, isHoliday(date) ? 'holy' : null));
                tr2.append(createHeadCell(date.format('HH'), 1, date.getDay() == 0 ? 'holyH' : null));
                trBody.append(createBodyCell(1, date.getHours() > 18, date.getDay() == 0 ? 'holy' : null));
                date.setHours(date.getHours() + 1);
            });
        } else {
            console.error("Wrong level " + zoom);
        }

        //set a minimal width
        computedTableWidth = Math.max(computedTableWidth, self.minGanttSize);

        var table = $("<table cellspacing=0 cellpadding=0>");
//        table.append(tr1).append(tr2).append(trBody).addClass("ganttTable").css({width: computedTableWidth});
        table.append(tr1).append(tr2).append(trBody).addClass("ganttTable").css({width: '100%'});
        table.height(self.master.editor.element.height());

        var box = $("<div>");
//        box.addClass("gantt unselectable").attr("unselectable", "true").css({position: "relative", width: computedTableWidth});
        box.addClass("gantt unselectable").attr("unselectable", "true").css({position: "relative", width: '100%', 'overflow': 'hidden'});
        box.append(table);

        //highlightBar
//        var hlb = $("<div>").addClass("ganttHighLight");
//        box.append(hlb);
//        self.highlightBar = hlb;

        //create link container
        var links = $("<div>");
//        links.addClass("ganttLinks").css({position: "absolute", top: 0, width: computedTableWidth, height: "100%"});
        links.addClass("ganttLinks").css({position: "absolute", top: 0, width: '100%', height: "100%"});
        box.append(links);

        //compute scalefactor fx
        self.computedTableWidth = computedTableWidth;
        self.fx = computedTableWidth / (endPeriod - startPeriod);

        // drawTodayLine
        var today_as_millis = new Date().getTime();
        if (today_as_millis > self.startMillis && today_as_millis < self.endMillis) {
//            var x = Math.round((today_as_millis - self.startMillis) * self.fx);
            var x = (today_as_millis - self.startMillis) / (originalEndMillis - originalStartMillis) * 100;
            var today = $("<div>").addClass("ganttToday").css("left", x + '%');
            box.append(today);
        }

        return box;
    }

    //if include today synch extremes
//    if (this.includeToday) {
//        var today = new Date().getTime();
//        originalStartMillis = originalStartMillis > today ? today : originalStartMillis;
//        originalEndMillis = originalEndMillis < today ? today : originalEndMillis;
//    }


    //get best dimension for gantt
//    console.debug('originalStartMillis : ', originalStartMillis);
//    console.debug('originalEndMillis   : ', originalEndMillis);
//    var period = getPeriod(zoom, originalStartMillis, originalEndMillis); //this is enlarged to match complete periods based on zoom level

    //console.debug(new Date(period.start) + "   " + new Date(period.end));
//    self.startMillis = period.start; //real dimension of gantt
//    self.endMillis = period.end;
    self.startMillis = originalStartMillis; //real dimension of gantt
    self.endMillis = originalEndMillis;
    self.originalStartMillis = originalStartMillis; //minimal dimension required by user or by task duration
    self.originalEndMillis = originalEndMillis;

//    var table = createGantt(zoom, period.start, period.end);
    var table = createGantt(zoom, originalStartMillis, originalEndMillis);

    return table;
};


//<%-------------------------------------- GANTT TASK GRAPHIC ELEMENT --------------------------------------%>
GanttDrawer.prototype.drawTask = function (task) {
    //console.debug("drawTask", task.name,new Date(task.start));
    
    // skip if it is not in the range
    if (task.start > this.originalEndMillis){
        return;
    }

    if (task.end < this.originalStartMillis){
        return;
    }
    
    var task_drawn_start = (task.start >= this.originalStartMillis) ? (task.start) : (this.originalStartMillis);
    var task_drawn_end   = (task.end  <= this.originalEndMillis)    ? (task.end)   : (this.originalEndMillis);

    var owners = [];
    if (this.master.grid_mode == 'Resource'){
        owners = task.resources;
    } else if (this.master.grid_mode == 'Task') {
//        owners.push(time_log.getTask());
        owners.push(task);
    }

    for (var i = 0; i < owners.length ; i++){
        var editorRow = owners[i].rowElement;

        var top = editorRow.position().top + this.master.editor.element.parent().scrollTop();
//        var x = Math.round((task_drawn_start - this.startMillis) * this.fx);
        var x = (task_drawn_start - this.startMillis) / (this.originalEndMillis - this.originalStartMillis) * 100;

        var taskBox;
        if (task.type != 'Project'){
            if (!task.isParent()) {
                // if it is a leaf task draw a TASKBAR
                if (this.master.grid_mode == 'Task'){
                    taskBox = $.JST.createFromTemplate(task, "TASKBAR");
                } else if (this.master.grid_mode == 'Resource') {
                    taskBox = $.JST.createFromTemplate(task, "TASKBAR_COMPACT");
                }
            } else {
                // draw a PARENTTASKBAR
                taskBox = $.JST.createFromTemplate(task, "PARENTTASKBAR");
            }
        } else {
            taskBox = $.JST.createFromTemplate(task, "PROJECTBAR");
        }
        
        //save row element on task
        task.ganttElements.push(taskBox);

//        taskBox.css({top: top, left: x, width: Math.round((task_drawn_end - task_drawn_start) * this.fx)});
        taskBox.css({
            top: top,
            left: x + '%',
            width: (task_drawn_end - task_drawn_start) / (this.originalEndMillis - this.originalStartMillis) * 100 + '%' 
        });

        var taskBoxSeparator = $("<div class='ganttLines'></div>");
        taskBoxSeparator.css({top: top + taskBoxSeparator.height()});

        this.element.append(taskBox);
        this.element.append(taskBoxSeparator);
    }
};

//<%-------------------------------------- GANTT TIMELOG GRAPHIC ELEMENT --------------------------------------%>
GanttDrawer.prototype.drawTimeLog = function (time_log) {
    //console.debug("drawTimeLog", time_log.name,new Date(time_log.start));
    // get the editor row of the resource

    var owner;
    if (this.master.grid_mode == 'Resource'){
        owner = time_log.getResource();
    } else if (this.master.grid_mode == 'Task') {
        owner = time_log.getTask();
    }

    var editorRow = owner.rowElement;
//    console.debug('Gantalendar.drawTimeLog: resource.rowElement:', editorRow);
    var top = editorRow.position().top + this.master.editor.element.parent().scrollTop();
//    console.debug('Gantalendar.drawTimeLog: top:', top);
    var x = Math.round((time_log.start - this.startMillis) * this.fx);

    var time_log_box;
    time_log_box = $.JST.createFromTemplate(time_log, "TIMELOGBAR");
    
    //save row element on timeLog
    time_log.ganttElement = time_log_box;

    time_log_box.css({top: top, left: x, width: Math.round((time_log.end - time_log.start) * this.fx)});

    var time_log_box_separator = $("<div class='ganttLines'></div>");
    time_log_box_separator.css({top: top + time_log_box_separator.height()});

    this.element.append(time_log_box);
//    this.element.append(time_log_box_separator);

};


//GanttDrawer.prototype.addTask = function (task) {
    //set new boundaries for gantt
//    this.originalEndMillis = this.originalEndMillis > task.end ? this.originalEndMillis : task.end;
//    this.originalStartMillis = this.originalStartMillis < task.start ? this.originalStartMillis : task.start;
//};


//<%-------------------------------------- GANT DRAW LINK ELEMENT --------------------------------------%>
//'from' and 'to' are tasks already drawn
GanttDrawer.prototype.drawLink = function (from, to, type) {
    var peduncolusSize = 10;
    var lineSize = 2;
    var self = this;

    // skip if from or to is not visible
    if (from.start > this.originalEndMillis || 
        from.end < this.originalStartMillis ||
        to.start > this.originalEndMillis || 
        to.end < this.originalStartMillis){
        // either from or to is not visible
        return;
    }

    var tableWidth = self.master.gantt.element.width();

    /**
     * A representation of a Horizontal line
     */
    HLine = function (width, top, left) {
        console.debug('--- HLINE ---');
        console.debug('width: ', width);
        console.debug('top  : ', top);
        console.debug('left : ', left);
        var hl = $("<div>").addClass("taskDepLine");
        hl.css({
            height: lineSize,
            left: left / tableWidth * 100 + '%', //left,
            width: width / tableWidth * 100 + '%',
            top: top - lineSize / 2
        });
        return hl;
    };

    /**
     * A representation of a Vertical line
     */
    VLine = function (height, top, left) {
        console.debug('--- VLINE ---');
        console.debug('height: ', height);
        console.debug('top  : ', top);
        console.debug('left : ', left);
        var vl = $("<div>").addClass("taskDepLine");
        vl.css({
            height: height,
            left: (left - lineSize / 2) / tableWidth * 100 + '%',
            width: lineSize,
            top: top
        });
        return vl;
    };

    /**
     * Given an item, extract its rendered position
     * width and height into a structure.
     */
    function buildRect(item) {
        if (item instanceof Task){
            var rect = item.ganttElements[0].position();
            rect.width = item.ganttElements[0].width();
            rect.height = item.ganttElements[0].height();
        } else {
            var rect = item.ganttElement.position();
            rect.width = item.ganttElement.width();
            rect.height = item.ganttElement.height();
        }
        return rect;
    }

    /**
     * The default rendering method, which paints a start to end dependency.
     *
     * @see buildRect
     */
    function drawStartToEnd(rectFrom, rectTo, peduncolusSize) {
        
        console.debug('drawStartToEnd.rectFrom : ', rectFrom);
        console.debug('drawStartToEnd.rectTo : ', rectTo);
        
        var left, top;

        var ndo = $("<div>").attr({
            from: from.id,
            to: to.id
        });

        var currentX = rectFrom.left + rectFrom.width;
        var currentY = rectFrom.height / 2 + rectFrom.top;

        var useThreeLine = (currentX + 2 * peduncolusSize) < rectTo.left;

        if (!useThreeLine) {
            // L1
            if (peduncolusSize > 0) {
                var l1 = new HLine(peduncolusSize, currentY, currentX);
                currentX = currentX + peduncolusSize;
                ndo.append(l1);
            }

            // L2
            var l2_4size = ((rectTo.top + rectTo.height / 2) - (rectFrom.top + rectFrom.height / 2)) / 2;
            var l2;
            if (l2_4size < 0) {
                l2 = new VLine(-l2_4size, currentY + l2_4size, currentX);
            } else {
                l2 = new VLine(l2_4size, currentY, currentX);
            }
            currentY = currentY + l2_4size;

            ndo.append(l2);

            // L3
            var l3size = rectFrom.left + rectFrom.width + peduncolusSize - (rectTo.left - peduncolusSize);
            currentX = currentX - l3size;
            var l3 = new HLine(l3size, currentY, currentX);
            ndo.append(l3);

            // L4
            var l4;
            if (l2_4size < 0) {
                l4 = new VLine(-l2_4size, currentY + l2_4size, currentX);
            } else {
                l4 = new VLine(l2_4size, currentY, currentX);
            }
            ndo.append(l4);

            currentY = currentY + l2_4size;

            // L5
            if (peduncolusSize > 0) {
                var l5 = new HLine(peduncolusSize, currentY, currentX);
                currentX = currentX + peduncolusSize;
                ndo.append(l5);

            }
        } else {
            //L1
            var l1_3Size = (rectTo.left - currentX) / 2;
            var l1 = new HLine(l1_3Size, currentY, currentX);
            currentX = currentX + l1_3Size;
            ndo.append(l1);

            //L2
            var l2Size = ((rectTo.top + rectTo.height / 2) - (rectFrom.top + rectFrom.height / 2));
            var l2;
            if (l2Size < 0) {
                l2 = new VLine(-l2Size, currentY + l2Size, currentX);
            } else {
                l2 = new VLine(l2Size, currentY, currentX);
            }
            ndo.append(l2);

            currentY = currentY + l2Size;

            //L3
            var l3 = new HLine(l1_3Size, currentY, currentX);
            currentX = currentX + l1_3Size;
            ndo.append(l3);
        }

        //arrow
        var arr = $("<div class='linkArrow'></div>").css({
            top: rectTo.top + rectTo.height / 2 - 5,
            left: (rectTo.left - 5) / tableWidth * 100 + '%'
        });

        ndo.append(arr);

        return ndo;
    }

    /**
     * A rendering method which paints a start to start dependency.
     *
     * @see buildRect
     */
    function drawStartToStart(rectFrom, rectTo, peduncolusSize) {
        var left, top;

        var ndo = $("<div>").attr({
            from: from.id,
            to: to.id
        });

        var currentX = rectFrom.left;
        var currentY = rectFrom.height / 2 + rectFrom.top;

        var useThreeLine = (currentX + 2 * peduncolusSize) < rectTo.left;

        if (!useThreeLine) {
            // L1
            if (peduncolusSize > 0) {
                var l1 = new HLine(peduncolusSize, currentY, currentX - peduncolusSize);
                currentX = currentX - peduncolusSize;
                ndo.append(l1);
            }

            // L2
            var l2_4size = ((rectTo.top + rectTo.height / 2) - (rectFrom.top + rectFrom.height / 2)) / 2;
            var l2;
            if (l2_4size < 0) {
                l2 = new VLine(-l2_4size, currentY + l2_4size, currentX);
            } else {
                l2 = new VLine(l2_4size, currentY, currentX);
            }
            currentY = currentY + l2_4size;

            ndo.append(l2);

            // L3
            var l3size = (rectFrom.left - peduncolusSize) - (rectTo.left - peduncolusSize);
            currentX = currentX - l3size;
            var l3 = new HLine(l3size, currentY, currentX);
            ndo.append(l3);

            // L4
            var l4;
            if (l2_4size < 0) {
                l4 = new VLine(-l2_4size, currentY + l2_4size, currentX);
            } else {
                l4 = new VLine(l2_4size, currentY, currentX);
            }
            ndo.append(l4);

            currentY = currentY + l2_4size;

            // L5
            if (peduncolusSize > 0) {
                var l5 = new HLine(peduncolusSize, currentY, currentX);
                currentX = currentX + peduncolusSize;
                ndo.append(l5);
            }
        } else {
            //L1

            var l1 = new HLine(peduncolusSize, currentY, currentX - peduncolusSize);
            currentX = currentX - peduncolusSize;
            ndo.append(l1);

            //L2
            var l2Size = ((rectTo.top + rectTo.height / 2) - (rectFrom.top + rectFrom.height / 2));
            var l2;
            if (l2Size < 0) {
                l2 = new VLine(-l2Size, currentY + l2Size, currentX);
            } else {
                l2 = new VLine(l2Size, currentY, currentX);
            }
            ndo.append(l2);

            currentY = currentY + l2Size;

            //L3

            var l3 = new HLine(peduncolusSize + (rectTo.left - rectFrom.left), currentY, currentX);
            currentX = currentX + peduncolusSize + (rectTo.left - rectFrom.left);
            ndo.append(l3);
        }

        //arrow
        var arr = $("<div class='linkArrow'></div>").css({
            top: rectTo.top + rectTo.height / 2 - 5,
            left: rectTo.left - 5
        });


        ndo.append(arr);

        return ndo;
    }

    var rectFrom = buildRect(from);
    var rectTo = buildRect(to);

    // Dispatch to the correct renderer
    if (type == 'start-to-start') {
        this.element.find(".ganttLinks").append(
            drawStartToStart(rectFrom, rectTo, peduncolusSize)
        );
    } else {
        this.element.find(".ganttLinks").append(
            drawStartToEnd(rectFrom, rectTo, peduncolusSize)
        );
    }
};


GanttDrawer.prototype.redrawLinks = function () {
    //console.debug("redrawLinks ");
    var self = this;
    this.element.stopTime("ganttlnksredr");
    this.element.oneTime(60, "ganttlnksredr", function () {
        //var prof=new Profiler("gd_drawLink_real");
        self.element.find(".ganttLinks").empty();
        for (var i = 0; i < self.master.links.length; i++) {
            var link = self.master.links[i];
            self.drawLink(link.from, link.to);
        }
        //prof.stop();
    });
};


GanttDrawer.prototype.reset = function () {
    this.element.find(".ganttLinks").empty();
    this.element.find("[dataId]").remove();
};


GanttDrawer.prototype.redrawTasks = function () {
    for (var i = 0; i < this.master.tasks.length; i++) {
        var task = this.master.tasks[i];
        if (this.master.grid_mode == 'Resource' && (task.type != 'Task' || !task.isLeaf())){
            continue;
        }
        this.drawTask(task);
    }
};

GanttDrawer.prototype.redrawTimeLogs = function () {
    for (var i = 0; i < this.master.time_logs.length; i++) {
        var time_log = this.master.time_logs[i];
        this.drawTimeLog(time_log);
    }
};


GanttDrawer.prototype.refreshGantt = function (kwargs) {
    if (kwargs){
        var start = kwargs['start'] || null;
        var end = kwargs['end'] || null;
        if (start && end){
            this.originalStartMillis = start;
            this.originalEndMillis = end;
        }
    }    
    //console.debug("refreshGantt");
    var par = this.element.parent();

    //try to maintain last scroll
    var scrollY = par.scrollTop();
    var scrollX = par.scrollLeft();

    this.element.remove();
    //guess the zoom level in base of period
    var days = (this.originalEndMillis - this.originalStartMillis) / (3600000 * 24);
    this.zoom = this.zoomLevels[days < 2 ? 0 : (days < 15 ? 1 : (days < 60 ? 2 : (days < 150 ? 3 : (days < 400 ? 4 : 5 ) ) ) )];

    var domEl = this.create(this.zoom, this.originalStartMillis, this.originalEndMillis);
    this.element = domEl;
    par.append(domEl);

    if (this.master.gantt_mode == 'Task'){
        this.redrawTasks();
        this.redrawLinks();
    } else if (this.master.gantt_mode == 'TimeLog') {
        this.redrawTimeLogs();
    }

    //set old scroll  
    //console.debug("old scroll:",scrollX,scrollY)
    par.scrollTop(scrollY);
    par.scrollLeft(scrollX);

    // redraw links
//    if (this.master.gantt_mode == 'Task'){
//        this.redrawLinks();
//    } 
    //set current task
//    if (this.master.currentTask) {
//        this.highlightBar.css("top", this.master.currentTask.ganttElement.position().top);
//    }
    this.bindEvents();
};

GanttDrawer.prototype.bindEvents = function() {
    // Drag event for zoom range
    var isDragging = false;
    this.element.mousedown(function(){
//        console.debug('drag start!');
        $(window).mousemove(function() {
            isDragging = true;
            $(window).unbind("mousemove");
        });
    }).mouseup(function(){
//        console.debug('drag end');
        var wasDragging = isDragging;
        isDragging = false;
        $(window).unbind("mousemove");
        if (!wasDragging) {
//            $("#throbble").toggle();
        }
    });
};

GanttDrawer.prototype.fitGantt = function () {
    delete this.zoom;
    this.refreshGantt();
};

GanttDrawer.prototype.centerOnToday = function () {
    //console.debug("centerOnToday");
    var x = Math.round(((new Date().getTime()) - this.startMillis) * this.fx);
    this.element.parent().scrollLeft(x);
};



