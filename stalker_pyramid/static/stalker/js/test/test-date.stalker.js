var Date = require('../date.stalker').Date;

exports['test Date.getClock() is working properly'] = function (test) {
    var test_date = new Date(1383579474543);
    test.equal(
        test_date.getClock(),
        56274543
    );
    test.done();
};

exports['test Date.setClock() is working properly'] = function (test) {
    var test_date = new Date(2013, 10, 4, 10, 0);
    test_date.setClock(56274543);
    test.equal(test_date.getTime(), 1383579474543);
    test.done();
};
