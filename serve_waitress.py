from waitress import serve

from app import create_app

app = create_app()

if __name__ == "__main__":
    serve(
        app,
        host=app.config["CONTROL_CENTER_HOST"],
        port=app.config["CONTROL_CENTER_PORT"],
        threads=app.config["CONTROL_CENTER_THREADS"],
        connection_limit=app.config["CONTROL_CENTER_CONNECTION_LIMIT"],
        channel_timeout=app.config["CONTROL_CENTER_CHANNEL_TIMEOUT"],
        ident="rpa-control-center",
    )