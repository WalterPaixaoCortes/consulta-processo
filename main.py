import json
import re
import sys
import os
from playwright.sync_api import Playwright, sync_playwright, expect
from solvecaptcha import Solvecaptcha

from dotenv import load_dotenv


load_dotenv()


def set_iframe_attr(page, selector, attr, value=None, remove=False):
    return page.evaluate(
        """
      ([sel, attr, val, remove]) => {
        const el = document.querySelector(sel);
        if (!el) return 'NOT_FOUND';
        if (remove) { el.removeAttribute(attr); return 'REMOVED'; }
        el.setAttribute(attr, val);
        return el.getAttribute(attr);
      }
    """,
        [selector, attr, value, remove],
    )


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        extra_http_headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        },
        #  storage_state="state.json",
    )
    page = context.new_page()
    page.goto("https://consultaunificadapje.tse.jus.br/#/public/inicial/index")

    page.get_by_role("textbox", name="CPF ou CNPJ").click()
    page.get_by_role("textbox", name="CPF ou CNPJ").fill("24.754.612/0001-38")

    ua = page.evaluate("() => navigator.userAgent")

    api_key = os.getenv("API", "YOUR_API_KEY")

    solver = Solvecaptcha(api_key, extendedResponse=True)

    try:
        result = solver.hcaptcha(
            sitekey=os.getenv("SITEKEY"),
            url="https://newassets.hcaptcha.com/captcha/v1/ac1807a0d7f33dc28c85051e92a750fde422071c/static/hcaptcha.html#frame=checkbox-invisible",
            userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        )
    except Exception as e:
        sys.exit(e)

    else:
        results = page.evaluate(
            """(token) => {
        const elh = document.querySelector("textarea[name='h-captcha-response']");
        if (!elh) return;
        elh.value = token;
        elh.setAttribute('value', token); // só para visualização
        elh.dispatchEvent(new Event('input', { bubbles: true }));
        elh.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
            result["code"],
        )

    with open("a.json", "w") as fw:
        fw.write(json.dumps(result))

    # set_iframe_attr(page, "iframe", "data-hcaptcha-response", result["code"])

    page.get_by_role("button", name="Pesquisar Pesquisar").click()

    # page2 = context.new_page()
    # page2.goto("https://consultaunificadapje.tse.jus.br/#/public/inicial/index")

    input("👉 Pressione ENTER para continuar...")

    # context.storage_state(path="state.json")

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
