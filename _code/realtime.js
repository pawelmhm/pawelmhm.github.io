"use strict";

function append_to_dom(data) {
    var data = JSON.parse(data)
    if (data.length == 0) {
        return
    }
    var blocks = data.map(function (question) {
        var block = "<div class='row'><div><span><a href='" + question.link;
        block += "'>" + question.title + "</span></a></div>";
        block += "<div><small>" + question.author + " "
        block += question.fetched + "</small></div></div>";
        return block;
    });
    $("#realtime").prepend(blocks).hide().fadeIn();
    $("#realtime").attr("modified", Date.now());
}

function doPoll() {
    $.ajax({
        url: "update",
        data: {
            "timestamp": parseInt($('#realtime').attr("modified") / 1000) || 0
        }
    }).done(function (data) {
        // append_to_dom(data);
    }).always(function () {
        setTimeout(doPoll, 5000);
    })
}


$(document).ready(function () {
    doPoll();
})
