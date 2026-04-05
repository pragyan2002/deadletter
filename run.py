from app import create_app
from app.alerting import start_alerting_thread

app = create_app()
start_alerting_thread(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
