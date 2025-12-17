from flask import Flask, render_template

app = Flask(__name__)


@app.get("/")
def index():
    """Render the home page."""
    return render_template("index.html")


if __name__ == "__main__":
    # Use 0.0.0.0 so the app is reachable from outside the container later.
    app.run(host="0.0.0.0", port=5000, debug=True)


