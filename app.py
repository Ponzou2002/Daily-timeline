from flask import Flask

app = Flask(__name__)


@app.get("/")
def index():
    return "<h1>Daily Timeline</h1><p>Flask is running.</p>"