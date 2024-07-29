from flask import Flask, render_template, request, jsonify
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('log-level=3')
    driver = webdriver.Chrome(options=options)
    return driver

# Initialize the WebDriver instance outside of the Flask application context

def get_new_link_from_redirect(redirect_url):
    driver = create_driver()
    try:
        driver.get(redirect_url)
        new_link = driver.current_url
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()
    return new_link


def get_show_link(show_name, season, episode):
    driver = create_driver()
    try:
        link = f"http://186.2.175.5/serie/stream/{show_name}/staffel-{season}/episode-{episode}"
        driver.get(link)
        element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#wrapper > div.seriesContentBox > div.container.marginBottom > div:nth-child('
                                      '5) > div.hosterSiteVideo > div.inSiteWebStream > div:nth-child(1) > iframe')))
        content_value = element.get_attribute('src')
        return content_value
    except Exception as e:
        return None

def get_video_link(show_name):
    driver = create_driver()
    try:
        link = f"https://cinemathek.net/filme/{show_name}"
        driver.get(link)
        try:
            iframe_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe.metaframe'))
            )
            src_url = iframe_element.get_attribute('src')
        except TimeoutException:
            print("Das iframe-Element konnte nicht innerhalb von 20 Sekunden gefunden werden.")
            src_url = None
    finally:
        driver.quit()
    return src_url

@app.route('/')
def index():

    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
        switch_value = request.form['switchValue']
        text_input = request.form['textInput'].replace(' ', '')
        show_name = text_input.strip()

        if switch_value == 'Movies':
            redirect_url = get_video_link(show_name)
            if redirect_url:
                new_url = get_new_link_from_redirect(redirect_url)
                return new_url
            else:
                return "Video Link not found"


        '''if switch_value == 'Shows':
            try:
                text_input = request.form['textInput'].replace(' ', '')
                show_name, season, episode = text_input.split(',')
                redirect_url = get_show_link(show_name, season, episode)
            except ValueError:
                return jsonify({"error": "Invalid input format for shows. Expected format: show_name,season,episode"}), 400
        elif switch_value == 'Movies':
            show_name = text_input.strip()
            redirect_url = get_video_link(show_name)
        else:
            return jsonify({"error": "Invalid switch value"}), 400

        if redirect_url:
            new_url = get_new_link_from_redirect(redirect_url)
            if new_url:
                return new_url
            else:
                return jsonify({"error": "Failed to retrieve new URL from redirect"}), 500
        else:
            return jsonify({"error": "Failed to retrieve redirect URL"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500
'''

if __name__ == '__main__':
    app.run(debug=True)

