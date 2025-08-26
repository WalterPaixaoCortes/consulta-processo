#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Selenium version of the Playwright script (with SolveCaptcha hCaptcha handling).

Usage:
  pip install selenium webdriver-manager python-dotenv solvecaptcha-python
  python selenium_main.py

Env vars expected:
  API=<your_solve_captcha_api_key>
  SITEKEY=<hcaptcha_sitekey_if_known>
"""

import os
import json
import time
import re
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from solvecaptcha import Solvecaptcha

load_dotenv()

TARGET_URL = "https://consultaunificadapje.tse.jus.br/#/public/inicial/index"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
CPF_CNPJ_EXEMPLO = "24.754.612/0001-38"


def make_driver(headless: bool = False) -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"--user-agent={USER_AGENT}")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    # Optional: less noisy logs
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(options=opts)
    return driver


def wait_visible_clickable(driver, by, selector, timeout=20):
    wait = WebDriverWait(driver, timeout)
    elem = wait.until(EC.presence_of_element_located((by, selector)))
    elem = wait.until(EC.visibility_of_element_located((by, selector)))
    elem = wait.until(EC.element_to_be_clickable((by, selector)))
    return elem


def find_cpf_cnpj_input(driver, timeout=10):
    """
    Try to locate a CPF/CNPJ textbox by common attributes (placeholder/name/id/aria-label)
    """
    wait = WebDriverWait(driver, timeout)

    xpaths = [
        # direct attributes (case-insensitive)
        "//*[(self::input or self::textarea) and "
        "(contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cpf') or "
        " contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cnpj') or "
        " contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cpf') or "
        " contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cnpj') or "
        " contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cpf') or "
        " contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cnpj') or "
        " contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cpf') or "
        " contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cnpj'))]",
        # by label text (label[for] -> input#id)
        "//label[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cpf') or "
        "        contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cnpj')]/@for",
    ]

    # First try attribute-based
    try:
        elems = driver.find_elements(By.XPATH, xpaths[0])
        for el in elems:
            try:
                if el.is_displayed() and el.is_enabled():
                    return el
            except Exception:
                continue
    except Exception:
        pass

    # Then try label-based association
    try:
        labels_for = driver.find_elements(By.XPATH, xpaths[1])
        for attr in labels_for:
            _for = (
                attr.get_attribute("value") if hasattr(attr, "get_attribute") else None
            )
            if _for:
                try:
                    el = driver.find_element(By.ID, _for)
                    if el.is_displayed() and el.is_enabled():
                        return el
                except Exception:
                    continue
    except Exception:
        pass

    return None


def inject_hcaptcha_and_submit(
    driver,
    token: str,
    submit_locator=(
        "xpath",
        "//button[contains(., 'Pesquisar') or contains(., 'PESQUISAR')]",
    ),
):
    """
    Inject hCaptcha response into hidden textarea and submit the form.
    """
    # 1) Inject token into main document
    driver.execute_script(
        """
        (function(tok){
            var el = document.querySelector("textarea[name='h-captcha-response']")
                  || document.querySelector("#h-captcha-response")
                  || document.querySelector("textarea.h-captcha-response")
                  || document.querySelector("input[name='h-captcha-response']");
            if(!el){
                el = document.createElement('textarea');
                el.name = 'h-captcha-response';
                el.style.display = 'none';
                document.body.appendChild(el);
            }
            el.value = tok;
            el.setAttribute('value', tok); // visual in DevTools
            el.dispatchEvent(new Event('input', {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
        })(arguments[0]);
        """,
        token,
    )

    # 2) Try to click the submit/search button
    by, sel = submit_locator
    by_map = {"xpath": By.XPATH, "css": By.CSS_SELECTOR, "name": By.NAME, "id": By.ID}
    _by = by_map.get(by.lower(), By.XPATH)

    # robust: try a few common patterns if default fails
    candidates = [
        (_by, sel),
        (
            By.XPATH,
            "//input[( @type='submit' or @type='button') and (contains(@value,'Pesquisar') or contains(@value,'PESQUISAR'))]",
        ),
        (
            By.XPATH,
            "//*[@role='button'][contains(., 'Pesquisar') or contains(., 'PESQUISAR')]",
        ),
        (
            By.XPATH,
            "//button//*[contains(., 'Pesquisar') or contains(., 'PESQUISAR')]/ancestor::button[1]",
        ),
        (By.XPATH, "//button"),
    ]

    for by_, s in candidates:
        try:
            btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((by_, s)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.3)
            btn.click()
            return True
        except Exception:
            continue
    return False


def main():
    api_key = os.getenv("API", "YOUR_API_KEY")
    sitekey_env = os.getenv("SITEKEY", None)

    driver = make_driver(headless=False)
    try:
        driver.get(TARGET_URL)

        input("👉 Pressione ENTER para continuar...")

        # Preencher CPF/CNPJ
        campo = find_cpf_cnpj_input(driver, timeout=15)
        if not campo:
            raise RuntimeError(
                "Não consegui localizar o campo CPF/CNPJ automaticamente."
            )
        campo.click()
        # limpar e digitar
        campo.send_keys(Keys.CONTROL, "a")
        campo.send_keys(Keys.DELETE)
        campo.send_keys(CPF_CNPJ_EXEMPLO)

        # Resolver hCaptcha via SolveCaptcha
        solver = Solvecaptcha(api_key, extendedResponse=True)

        if sitekey_env:
            sitekey = sitekey_env
        else:
            # tentar localizar sitekey no DOM/iframe (básico)
            sitekey = None
            try:
                # data-sitekey on div.h-captcha
                sitekey = driver.execute_script(
                    "return document.querySelector('div.h-captcha[data-sitekey]')?.getAttribute('data-sitekey') || null;"
                )
            except Exception:
                sitekey = None

        if not sitekey:
            print(
                "⚠️ SITEKEY não encontrado no DOM. Usando valor de ambiente ou configure manualmente."
            )
            sitekey = os.getenv("SITEKEY", "")

        if not sitekey:
            raise RuntimeError(
                "Sitekey não definido. Configure SITEKEY no .env ou ajuste a lógica de detecção."
            )

        try:
            result = solver.hcaptcha(sitekey=sitekey, url=TARGET_URL)
        except Exception as e:
            raise SystemExit(e)

        token = (
            result["code"]
            if isinstance(result, dict) and "code" in result
            else (result if isinstance(result, str) else "")
        )
        if not token:
            raise RuntimeError(f"Retorno inesperado do solver: {result}")

        # salvar resposta para inspeção
        with open("a.json", "w", encoding="utf-8") as fw:
            fw.write(json.dumps(result, ensure_ascii=False, indent=2))

        # pausa para debug
        input("👉 Token pronto. Pressione ENTER para injetar e pesquisar...")

        ok = inject_hcaptcha_and_submit(driver, token)
        if not ok:
            print(
                "⚠️ Não consegui clicar no botão de pesquisa automaticamente. Tente clicar manualmente."
            )
            input("👉 Clique manualmente e pressione ENTER para continuar...")

        input("👉 Pressione ENTER para finalizar...")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
