export function register() {}

export function unregister() {
  if ('serviceWorker' in navigator) {
    try {
      navigator.serviceWorker.getRegistrations?.().then((regs) => regs.forEach((r) => r.unregister()));
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Service worker unregistration failed:', err);
    }
  }
}

export default { register, unregister };
