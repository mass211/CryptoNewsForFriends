from flask import Flask
from fetch import fetch_and_send_all

app = Flask(__name__)

@app.route('/')
def home():
    return "Crypto Bot is running!"

@app.route('/run')
def run_job():
    try:
        fetch_and_send_all()
        return 'Task executed successfully.'
    except Exception as e:
        return f'Error running task: {e}'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
