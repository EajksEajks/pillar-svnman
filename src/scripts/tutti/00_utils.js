
/* Returns a more-or-less reasonable message given an error response object. */
function xhrErrorResponseMessage(err) {
    console.log(err);
    if (typeof err.responseJSON == 'undefined')
        return err.statusText;

    if (typeof err.responseJSON._error != 'undefined' && typeof err.responseJSON._error.message != 'undefined')
        return err.responseJSON._error.message;

    if (typeof err.responseJSON._message != 'undefined')
        return err.responseJSON._message

    return err.statusText;
}

function xhrErrorResponseElement(err, prefix) {
    msg = xhrErrorResponseMessage(err);
    return $('<span>')
        .text(prefix + msg);
}
