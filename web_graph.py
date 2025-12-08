from flask import Flask, render_template, jsonify
import csv

app = Flask(__name__)

filename = "pressure_test_data.csv"

@app.route("/")
def index():
    return render_template("csv_graph.html")

@app.route("/data")
def data():
    labels = []  # axis X – time
    values = []  # axis Y – pressure

    try:
        with open(filename, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                labels.append(row["time"])
                values.append(float(row["pressure"]))
        return jsonify(labels=labels, values=values)

    except Exception as e:
        print(f"Chyba při čtení CSV: {e}")
        return jsonify(error=str(e)), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5008, debug=True)