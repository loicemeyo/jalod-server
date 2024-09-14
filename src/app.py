from dotenv import load_dotenv
import os

from flask import Flask
app = Flask(__name__)
@app.route('/')
def hello_world():
    return "Hi mama Jiwa <3"

if __name__ == '__main__':
    app.run(debug=True)