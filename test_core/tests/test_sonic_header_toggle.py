import pathlib
import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import sync_playwright

# Regression test for header badge toggles

def test_badge_toggles():
    js = pathlib.Path('static/js/sonic_header.js').read_text(encoding='utf-8')
    # stub feather and fetch behaviour
    stub_js = """
    window.feather = {
      replace: () => {},
      icons: {
        thermometer: { toSvg: opts => `<svg id="${opts.id}" data-icon="thermometer"></svg>` },
        percent: { toSvg: opts => `<svg id="${opts.id}" data-icon="percent"></svg>` },
        'dollar-sign': { toSvg: opts => `<svg id="${opts.id || ''}" data-icon="dollar"></svg>` },
        clock: { toSvg: opts => `<svg id="${opts.id || ''}" data-icon="clock"></svg>` }
      }
    };
    window.fetch = async (url) => {
      if(url.includes('profit_total')) return { json: async () => ({ profit: 20 }) };
      if(url.includes('profit')) return { json: async () => ({ profit: 5 }) };
      if(url.includes('profit_wallet_icon')) return { json: async () => ({ icon: '/foo.jpg' }) };
      if(url.includes('travel')) return { json: async () => ({ travel_percent: 5 }) };
      if(url.includes('heat')) return { json: async () => ({ heat_percentage: 10 }) };
      if(url.includes('interval')) return { json: async () => ({ interval_seconds: 60, seconds_remaining: 60 }) };
      return { json: async () => ({}) };
    };
    """
    html = f"""
    <html><body>
    <div id='profitBadge' class='badge profit-badge' title='Wallet profit'><span id='profitIcon'><i data-feather='dollar-sign'></i></span> <span id='profitValue'></span></div>
    <div id='heatBadge' class='badge heat-badge' data-heat-limit='90' data-travel-limit='80' title='Heat ≥ 90, Travel ≤ -80'><i id='heatIcon' data-feather='thermometer'></i> <span id='heatValue'></span></div>
    <script>{stub_js}</script>
    <script>{js}</script>
    </body></html>
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        page.wait_for_selector('#heatBadge')

        assert page.inner_text('#profitValue') == '5'
        assert page.inner_text('#heatValue') == '10'
        assert page.get_attribute('#heatIcon', 'data-icon') == 'thermometer'
        assert page.query_selector('#profitIcon img') is not None

        page.click('#profitBadge')
        page.click('#heatBadge')
        assert page.inner_text('#profitValue') == '20'
        assert page.inner_text('#heatValue') == '5'
        assert page.get_attribute('#heatIcon', 'data-icon') == 'percent'
        assert page.query_selector('#profitIcon img') is None

        page.click('#profitBadge')
        page.click('#heatBadge')
        assert page.inner_text('#profitValue') == '5'
        assert page.inner_text('#heatValue') == '10'
        assert page.get_attribute('#heatIcon', 'data-icon') == 'thermometer'
        assert page.query_selector('#profitIcon img') is not None

        browser.close()
