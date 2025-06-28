import pathlib
from playwright.sync_api import sync_playwright


def test_sleep_icon_when_monitor_inactive():
    js = pathlib.Path('static/js/sonic_header.js').read_text(encoding='utf-8')
    stub_js = """
    window.feather = {
      replace: () => {},
      icons: {
        clock: { toSvg: opts => `<svg id='${opts.id || ''}' data-icon='clock'></svg>` }
      }
    };
    window.fetch = async (url) => {
      if(url.includes('interval')) return { json: async () => ({ interval_seconds: 60, seconds_remaining: 60 }) };
      if(url.includes('ledger_ages')) return { json: async () => ({ age_cyclone: 9999 }) };
      return { json: async () => ({}) };
    };
    """
    html = f"""
    <html><body>
    <div class='badge timer-badge'><i data-feather='clock'></i> <span id='countdown'>0</span>s</div>
    <script>{stub_js}</script>
    <script>{js}</script>
    </body></html>
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        page.wait_for_selector('#countdown')
        assert page.inner_text('#countdown') == '💤'
        browser.close()
