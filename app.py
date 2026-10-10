from flask import Flask, render_template
import random

app = Flask(__name__)

@app.route('/')
def home():

    data = {
        "vehicle_id":"VH001",
        "speed": random.randint(20,120),
        "battery": random.randint(40,100),
        "temperature": random.randint(30,80),
        "ota_version":"v1.0.6",
        "status":"Connected"
    }

    return render_template("index.html",data=data)


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000)