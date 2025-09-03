from .base import AutoRequest
from .web_browser import (
    WebBrowserRequest,
    CloseBrowserRequest,
    BrowserStatusRequest,
    JupiterConnectRequest,
    RegisterWalletRequest,
    WebBrowserWithWalletRequest,
    CloseWalletRequest,
)

__all__ = [
    "AutoRequest",
    "WebBrowserRequest",
    "CloseBrowserRequest",
    "BrowserStatusRequest",
    "JupiterConnectRequest",
    "RegisterWalletRequest",
    "WebBrowserWithWalletRequest",
    "CloseWalletRequest",
]
