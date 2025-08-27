import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
)


# API configuration and target URL
API_KEY = "66900abf147f9706181fd22edb62aeb3"
PAGEURL = "https://nopecha.com/captcha/hcaptcha"


def solve_hcaptcha(sitekey):
    # Step 1: Send a request to obtain captcha_id using the dynamic sitekey

    in_url = "https://api.solvecaptcha.com/in.php"
    payload = {
        "key": API_KEY,
        "method": "hcaptcha",
        "sitekey": sitekey,
        "pageurl": PAGEURL,
        "json": 1,
    }

    print(payload)
    response = requests.post(in_url, data=payload)
    result = response.json()

    if result.get("status") != 1:
        print("Error sending request:", result.get("request"))
        return None

    captcha_id = result.get("request")
    print("Received captcha_id:", captcha_id)

    # Step 2: Poll for the captcha solution
    res_url = "https://api.solvecaptcha.com/res.php"
    while True:
        params = {"key": API_KEY, "action": "get", "id": captcha_id, "json": 1}
        res = requests.get(res_url, params=params)
        data = res.json()

        if data.get("status") == 1:
            print("Captcha solved successfully!")
            return data  # The response contains the token and useragent
        elif data.get("request") == "CAPCHA_NOT_READY":
            print("Captcha not ready yet, waiting 5 seconds...")
            time.sleep(5)
        else:
            print("Error retrieving solution:", data.get("request"))
            return None


def set_captcha_token(driver, token):
    # Find or create hidden fields for hCaptcha and reCaptcha
    try:
        driver.find_element(By.NAME, "h-captcha-response")
    except Exception:
        driver.execute_script(
            """
            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'h-captcha-response';
            document.body.appendChild(input);
        """
        )
    try:
        driver.find_element(By.NAME, "g-recaptcha-response")
    except Exception:
        driver.execute_script(
            """
            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'g-recaptcha-response';
            document.body.appendChild(input);
        """
        )
    # Insert the token into the fields
    driver.execute_script(
        f"""
        document.getElementsByName('h-captcha-response')[0].value = '{token}';
        document.getElementsByName('g-recaptcha-response')[0].value = '{token}';
    """
    )


def show_visual_feedback(driver):
    # Create a banner on the page to indicate that the captcha has been solved
    driver.execute_script(
        """
        var banner = document.createElement('div');
        banner.innerText = 'Captcha Solved!';
        banner.style.position = 'fixed';
        banner.style.top = '0';
        banner.style.left = '0';
        banner.style.width = '100%';
        banner.style.backgroundColor = 'green';
        banner.style.color = 'white';
        banner.style.fontSize = '24px';
        banner.style.fontWeight = 'bold';
        banner.style.textAlign = 'center';
        banner.style.zIndex = '9999';
        banner.style.padding = '10px';
        document.body.appendChild(banner);
    """
    )


LOWER_FROM = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER_TO = "abcdefghijklmnopqrstuvwxyz"


def _ci(text):
    return text.lower()


def _x_contains_ci(expr, needle):
    # contains(translate(EXPR, 'ABC..', 'abc..'), 'needle')
    return f"contains(translate({expr}, '{LOWER_FROM}', '{LOWER_TO}'), '{_ci(needle)}')"


def click_button_by_name(driver, name, timeout=10):
    """
    Emula Playwright get_by_role('button', { name }) no Selenium.
    Tenta por texto, aria-label, title, value, e role=button. Espera ficar clicável.
    """
    wait = WebDriverWait(driver, timeout)

    XPATHS = [
        # <button> pelo texto visível:
        f"//button[{_x_contains_ci('normalize-space(.)', name)}]",
        # <button> por aria-label / title:
        f"//button[{_x_contains_ci('@aria-label', name)} or {_x_contains_ci('@title', name)}]",
        # <input type=submit|button|reset> pelo value/aria-label/title:
        f"//input[( @type='submit' or @type='button' or @type='reset') and "
        f"({_x_contains_ci('@value', name)} or {_x_contains_ci('@aria-label', name)} or {_x_contains_ci('@title', name)})]",
        # qualquer elemento com role='button' por texto/aria-label/title:
        f"//*[@role='button' and ({_x_contains_ci('normalize-space(.)', name)} or "
        f"{_x_contains_ci('@aria-label', name)} or {_x_contains_ci('@title', name)})]",
        # links estilizados como botão
        f"//a[@role='button' and ({_x_contains_ci('normalize-space(.)', name)} or "
        f"{_x_contains_ci('@aria-label', name)} or {_x_contains_ci('@title', name)})]",
    ]

    last_err = None
    for xp in XPATHS:
        try:
            el = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
            # garantir que está no viewport e sem overlay
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            try:
                el.click()
            except ElementClickInterceptedException:
                # overlay? tente esperar um pouco e clicar de novo, ou usar JS click como último recurso
                time.sleep(0.5)
                el = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                try:
                    el.click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", el)
            return True
        except Exception as e:
            last_err = e
            continue
    # Se chegou aqui, não encontrou/clicou
    raise TimeoutException(
        f"Botão com nome '{name}' não encontrado/clicável. Último erro: {last_err}"
    )


def main():
    # Initialize Selenium WebDriver (Chrome)
    driver = webdriver.Chrome()
    driver.get(PAGEURL)

    # Wait for the element with data-sitekey to appear on the page
    try:
        sitekey_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-sitekey]"))
        )
        # Dynamically extract the sitekey
        sitekey = sitekey_element.get_attribute("data-sitekey")
        print("Extracted sitekey:", sitekey)
    except Exception as e:
        print("Failed to find element with data-sitekey:", e)
        driver.quit()
        return

    # Solve hCaptcha using the dynamically extracted sitekey
    solution = solve_hcaptcha(sitekey)
    if solution:
        token = solution.get("request")
        user_agent = solution.get("useragent")
        print("Received token:", token)
        print("User-Agent:", user_agent)

        # Insert the token into the hidden form fields
        set_captcha_token(driver, token)
        print("Token successfully inserted into the form fields.")

        # Display visual feedback indicating that the captcha has been solved
        show_visual_feedback(driver)

        # cpfcnpj = driver.find_element(By.CSS_SELECTOR, 'input[name="cpfCnpjParte"]')
        # cpfcnpj.send_keys("24.754.612/0001-38")

        # If needed, the form can be automatically submitted:
        # click_button_by_name(driver, "Pesquisar")

        # Keep the browser open for demonstration (10 seconds)
        time.sleep(60)
        driver.quit()
    else:
        print("Failed to solve the captcha.")
        driver.quit()


if __name__ == "__main__":
    main()
