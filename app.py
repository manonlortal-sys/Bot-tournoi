from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot tournoi en ligne", 200