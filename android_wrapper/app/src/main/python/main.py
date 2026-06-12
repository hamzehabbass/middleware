from middleware import run_flask_server

# This is the entrypoint called by the Android wrapper.

def run_server():
    run_flask_server(host='127.0.0.1', port=5000)
