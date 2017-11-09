
/* Returns a more-or-less reasonable message given an error response object. */
function xhrErrorResponseMessage(err) {
    if (err.readyState == 0 || err.status == 0)
        return "Connection refused; either the server is unreachable or your internet connection is down.";

    if (err.status == 451) {
        return "This user has no Subversion usage in their subscription package.";
    }

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

var Password = {
    _pattern: /[a-hj-np-zA-HJ-NP-Z2-9_\-\+'?!]/,

    _getRandomByte: function() {
        // http://caniuse.com/#feat=getrandomvalues
        if (window.crypto && window.crypto.getRandomValues) {
            var result = new Uint8Array(1);
            window.crypto.getRandomValues(result);
            return result[0];
        } else if (window.msCrypto && window.msCrypto.getRandomValues) {
            var result = new Uint8Array(1);
            window.msCrypto.getRandomValues(result);
            return result[0];
        } else {
            return Math.floor(Math.random() * 256);
        }
    },

    generate: function(length) {
        return Array.apply(null, {
                'length': length
            })
            .map(function() {
                var result;
                while (true) {
                    result = String.fromCharCode(this._getRandomByte());
                    if (this._pattern.test(result)) {
                        return result;
                    }
                }
            }, this)
            .join('');
    }
};
