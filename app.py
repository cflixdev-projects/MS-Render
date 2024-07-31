from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import os
from werkzeug.utils import secure_filename
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the uploads directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize the WebDriver instance outside of the Flask application context
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument('log-level=3')
driver = webdriver.Chrome(options=options)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_new_link_from_redirect(driver, redirect_url):
    driver.get(redirect_url)
    new_link = driver.current_url
    print('aktueller neuere link ' + new_link)
    return new_link

def get_video_link(driver, show_name, season=None, episode=None):
    if season and episode:
        link = f"http://186.2.175.5/serie/stream/{show_name}/staffel-{season}/episode-{episode}"
    else:
        link = f"https://cinemathek.net/filme/{show_name}"

    driver.get(link)

    if season and episode:
        element = driver.find_element(By.CSS_SELECTOR,
                                      '#wrapper > div.seriesContentBox > div.container.marginBottom > div:nth-child('
                                      '5) > div.hosterSiteVideo > div.inSiteWebStream > div:nth-child(1) > iframe')
        content_value = element.get_attribute('src')
    else:
        try:
            iframe_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe.metaframe'))
            )
            content_value = iframe_element.get_attribute('src')
        except TimeoutException:
            print("Das iframe-Element konnte nicht innerhalb von 20 Sekunden gefunden werden.")
            content_value = None

    print('content_value = ' + content_value)
    return content_value

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify(error="No file part"), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(error="No selected file"), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify(imageURL=url_for('uploaded_file', filename=filename))
    return jsonify(error="File not allowed"), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/images', methods=['GET'])
def list_images():
    files = os.listdir(UPLOAD_FOLDER)
    image_urls = [url_for('uploaded_file', filename=f) for f in files if allowed_file(f)]

    images_html = ''.join(
        f'<img src="{url}" style="height: 50vh; width: auto; margin: 10px; max-width: 100%; object-fit: cover;">' for
        url in image_urls
    )

    # Define the complete HTML response with inline CSS
    html_response = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Image Gallery</title>
        <style>
        * {{
        margin: 0;
        padding: 0;
        }}
            body {{
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                background-color: #222;
            }}
            .image-container {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                align-items: center;
                max-width: 100%;
                padding: 10px;
                box-sizing: border-box;
            }}
            .image-container img {{
            border-radius: 15px;
                height: 50vh; /* Adjust as needed */
                width: auto;
                max-width: 100%;
                object-fit: cover;
            }}
        </style>
    </head>
    <body>
        <div class="image-container">
            {images_html}
        </div>
    </body>
    </html>
    '''

    return html_response


@app.route('/search', methods=['POST'])
def search():
    text_input = request.form['textInput'].replace(' ', '')
    inputs = text_input.split(',')

    if len(inputs) == 3:
        show_name, season, episode = inputs
        redirect_url = get_video_link(driver, show_name, season, episode)
    else:
        show_name = inputs[0]
        redirect_url = get_video_link(driver, show_name)

    if redirect_url:
        new_url = get_new_link_from_redirect(driver, redirect_url)
        return new_url
    else:
        return "Video link not found", 404

if __name__ == '__main__':
    app.run(debug=True)
