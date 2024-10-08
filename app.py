from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import os
from werkzeug.utils import secure_filename
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import logging

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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_new_link_from_redirect(driver, redirect_url):
    driver.get(redirect_url)
    new_link = driver.current_url
    logger.info(f'New link from redirect: {new_link}')
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
            logger.error("The iframe element could not be found within 20 seconds.")
            content_value = None

    logger.info(f'Content value: {content_value}')
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
        logger.info(f'File uploaded: {filename}')
        return jsonify(imageURL=url_for('uploaded_file', filename=filename))
    return jsonify(error="File not allowed"), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/images', methods=['GET'])
def list_images():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)]
    files_with_mtime = [(f, os.path.getmtime(os.path.join(UPLOAD_FOLDER, f))) for f in files]
    sorted_files = sorted(files_with_mtime, key=lambda x: x[1], reverse=True)

    image_urls = [url_for('uploaded_file', filename=f[0]) for f in sorted_files]

    images_html = ''.join(
        f'<img src="{url}" style="height: 500px; width: auto; margin: 10px; object-fit: cover;">' for
        url in image_urls
    )

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
        background-color: rgb(21, 21, 21);
        display: flex;
                flex-wrap: wrap;
                flex-direction: column;
                justify-content: center;
                align-items: center;
        }}
            .image-container {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                align-items: center;
                max-width: 60%;
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
         <script>
            function updateGallery() {{
                fetch('/images')
                    .then(response => response.text())
                    .then(data => {{
                        document.querySelector('.image-container').innerHTML = new DOMParser()
                            .parseFromString(data, 'text/html')
                            .querySelector('.image-container').innerHTML;
                        console.log('Gallery URL:', window.location.href + 'images');
                    }})
                    .catch(error => console.error("Error fetching the gallery: " + error));
            }}

            // Periodically update the gallery
            setInterval(updateGallery, 5000); // Update every 5 seconds
        </script>
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
        logger.info(f'Searching for show: {show_name}, season: {season}, episode: {episode}')
        redirect_url = get_video_link(driver, show_name, season, episode)
    else:
        show_name = inputs[0]
        logger.info(f'Searching for show: {show_name}')
        redirect_url = get_video_link(driver, show_name)

    if redirect_url:
        new_url = get_new_link_from_redirect(driver, redirect_url)
        logger.info(f'Redirect URL: {new_url}')
        return new_url
    else:
        logger.error('Video link not found')
        return "Video link not found", 404

if __name__ == '__main__':
    app.run(debug=True)