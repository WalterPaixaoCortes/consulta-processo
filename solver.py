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


def run(cnpj: str) -> bool:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(
            extra_http_headers={"User-Agent": os.getenv("USERAGENT")},
        )
        page = context.new_page()
        page.goto(os.getenv("URL"))

        page.get_by_role("textbox", name="CPF ou CNPJ").click()
        page.get_by_role("textbox", name="CPF ou CNPJ").fill(cnpj)

        ua = page.evaluate("() => navigator.userAgent")

        api_key = os.getenv("API", "YOUR_API_KEY")

        solver = Solvecaptcha(api_key, extendedResponse=True)

        try:
            result = solver.hcaptcha(
                sitekey=os.getenv("SITEKEY"),
                url=os.getenv("URLCAPTCHA"),
                userAgent=os.getenv("USERAGENT"),
            )
        except Exception as e:
            return None

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

        set_iframe_attr(page, "iframe", "data-hcaptcha-response", result["code"])

        page.get_by_role("button", name="Pesquisar Pesquisar").click()

        input("👉 Pressione ENTER para continuar...")

        # ---------------------
        context.close()
        browser.close()
        return {"status": "success"}


if __name__ == "__main__":
    cnpj = sys.argv[1] if len(sys.argv) > 1 else "000.000.000-00"
    run(cnpj)
