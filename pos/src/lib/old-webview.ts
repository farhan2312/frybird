// Polyfills for the SUNMI T2s counter terminal, whose Chromium 81 engine can't be updated.
if (!Array.prototype.at) {
  const at = function (this: { length: number; [index: number]: unknown }, index: number) {
    const position = Math.trunc(index) || 0;
    return this[position < 0 ? this.length + position : position];
  };
  Object.defineProperty(Array.prototype, 'at', { value: at, writable: true, configurable: true });
  Object.defineProperty(String.prototype, 'at', { value: at, writable: true, configurable: true });
}
if (!Object.hasOwn) {
  Object.hasOwn = (target: object, key: PropertyKey) => Object.prototype.hasOwnProperty.call(target, key);
}
if (window.crypto && !window.crypto.randomUUID) {
  window.crypto.randomUUID = () =>
    '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, (c) =>
      (Number(c) ^ (window.crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (Number(c) / 4)))).toString(16)
    ) as ReturnType<Crypto['randomUUID']>;
}

const probe = document.createElement('div');
probe.style.cssText = 'display:flex;flex-direction:column;row-gap:1px;position:absolute';
probe.append(document.createElement('div'), document.createElement('div'));
document.documentElement.append(probe);
if (probe.scrollHeight !== 1) {
  document.documentElement.classList.add('no-flex-gap');
}
probe.remove();
