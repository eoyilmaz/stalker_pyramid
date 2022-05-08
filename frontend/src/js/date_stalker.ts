
import * as moment from "moment";

declare global{
    interface Date {
        getClock(): number;
        setClock(number): Date;
        format(String): String;
    }
}


// extend the Date object to include getClock(), setClock()
/**
 * Returns the UTC clock as milliseconds
 * 
 * @returns {Number}
 */
Date.prototype.getClock = function () {
    return this.getTime() % 86400000;
};

/**
 * Sets the UTC clock of the Date object
 * 
 * @param {Number} clock
 *  The clock in milliseconds
 * 
 */
Date.prototype.setClock = function (clock) {
    'use strict';
    let temp_clock = +clock,
        time = this.getTime();
    this.setTime(time - time % 86400000 + temp_clock % 86400000);
    return this;
};


Date.prototype.format = function (format_template) {
    return moment(this).format(format_template);
}