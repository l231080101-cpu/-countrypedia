from flask import jsonify


def api_response(data=None, status=200, error=None):
    body = {}
    if error:
        body["error"] = error
    if data is not None:
        body = data
    return jsonify(body), status


def error_response(message, status=400):
    return api_response(error=message, status=status)
