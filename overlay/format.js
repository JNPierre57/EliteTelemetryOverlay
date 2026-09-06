(function (root) {
  function formatCredits(value, separator = ' ', decimals = 0) {
    if (!Number.isSafeInteger(value) || value < 0) throw new Error('Invalid credits');
    return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, () => separator) + (decimals ? '.' + '0'.repeat(decimals) : '');
  }
  root.formatCredits = formatCredits;
  if (typeof module !== 'undefined') module.exports = { formatCredits };
})(globalThis);
