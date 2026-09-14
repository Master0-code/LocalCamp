import flask_socketio

_original_run = flask_socketio.SocketIO.run

def patched_run(self, app, *args, **kwargs):
    kwargs["allow_unsafe_werkzeug"] = True
    return _original_run(self, app, *args, **kwargs)

flask_socketio.SocketIO.run = patched_run
