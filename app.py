from flask import Flask, render_template, redirect, send_file, request, jsonify
import csv, os
from scraper import main as run_scraper  # import the main() from your scraper

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', data=None)

@app.route('/scrape', methods=['POST'])
def scrape():
    run_scraper()  # calls scraper.py main function
    return jsonify({'status': 'done'})

@app.route('/data')
def data():
    import csv
    if os.path.exists('rera_projects.csv'):
        with open('rera_projects.csv', newline='', encoding='utf-8') as f:
            data = list(csv.DictReader(f))
        return jsonify(data)
    return jsonify([])


@app.route('/download')
def download():
    return send_file('rera_projects.csv', as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
