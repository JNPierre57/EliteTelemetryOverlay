(function (root) {
  function formatCredits(value, separator = ' ', decimals = 0) {
    if (!Number.isSafeInteger(value) || value < 0) throw new Error('Invalid credits');
    return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, () => separator) + (decimals ? '.' + '0'.repeat(decimals) : '');
  }
  function shouldAnimate(previous, value, duration, reducedMotion, mode = 'auto') {
    return previous !== null && value > previous && duration > 0 && mode !== 'never' && (mode === 'always' || !reducedMotion);
  }
  root.shouldAnimate = shouldAnimate;
  root.formatCredits = formatCredits;
  if (typeof module !== 'undefined') module.exports = { formatCredits, shouldAnimate };
})(globalThis);
