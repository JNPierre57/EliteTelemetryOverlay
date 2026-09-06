'use strict';
const digits = document.querySelector('#digits');
const status = document.querySelector('#status');
const main = document.querySelector('main');
const parameters = new URLSearchParams(location.search);
const motionMode = parameters.get('motion') || 'auto';
const demo = parameters.get('demo') === '1';
const demoValues = [1000000000, 1025000000, 2450000000, 12847563420, 12847563420, 250];
const demoStart = performance.now();
let settings, current = null, animations = [], cleanup = null;
function fit() {
  main.style.transform = `scale(${Math.min(1, innerWidth / main.offsetWidth)})`;
}
function render(value) {
  if (value === current) return;
  clearTimeout(cleanup);
  animations.forEach(animation => animation.cancel());
  animations = [];
  const text = formatCredits(value, settings.thousands_separator, settings.decimals);
  const previous = current === null ? '' : formatCredits(current, settings.thousands_separator, settings.decimals).padStart(text.length, '0');
  const animate = shouldAnimate(current, value, settings.animation_ms, matchMedia('(prefers-reduced-motion: reduce)').matches, motionMode);
  current = value;
  digits.replaceChildren();
  [...text].forEach((character, index) => {
    const column = document.createElement('span');
    column.className = /[0-9]/.test(character) ? 'digit' : 'separator';
    if (column.className === 'separator') column.textContent = character;
    else {
      const reel = document.createElement('span');
      reel.className = 'reel';
      const start = Number(previous[index]) || 0;
      const steps = animate ? 10 + (Number(character) - start + 10) % 10 : 0;
      for (let i = 0; i <= steps; i++) {
        const cell = document.createElement('span');
        cell.textContent = steps ? (start + i) % 10 : character;
        reel.append(cell);
      }
      column.append(reel);
      if (animate) animations.push(reel.animate([{transform: 'translateY(0)'}, {transform: `translateY(-${steps * 1.15}em)`}], {duration: settings.animation_ms * (.8 + .2 * index / text.length), easing: 'cubic-bezier(.15,.65,.2,1)', fill: 'forwards'}));
    }
    digits.append(column);
  });
  document.querySelector('#counter').setAttribute('aria-label', text + ' ' + settings.suffix);
  fit();
  if (animate) cleanup = setTimeout(() => {
    animations.forEach(animation => animation.cancel());
    animations = [];
    digits.textContent = text;
    fit();
  }, settings.animation_ms + 30);
}
async function poll() {
  try {
    if (!settings) {
      const response = await fetch('/api/config', {signal: AbortSignal.timeout(3000)});
      if (!response.ok) throw new Error();
      settings = await response.json();
      document.querySelector('#label').textContent = settings.label;
      document.querySelector('#suffix').textContent = settings.suffix;
      document.body.style.fontFamily = settings.font_family;
      document.documentElement.style.setProperty('--size', settings.font_size + 'px');
    }
    let data;
    if (demo) {
      data = {value: demoValues[Math.floor((performance.now() - demoStart) / 2500) % demoValues.length], source: 'demo'};
    } else {
      const response = await fetch('/api/value', {signal: AbortSignal.timeout(3000)});
      if (!response.ok) throw new Error();
      data = await response.json();
    }
    if (data.value !== null) render(data.value);
    status.textContent = data.source === 'demo' ? 'DEMO' : data.value === null ? 'Waiting for EDEB data' : '';
  } catch {
    status.textContent = 'Receiver unavailable · last known value';
  } finally {
    setTimeout(poll, settings ? settings.poll_ms : 1000);
  }
}
addEventListener('resize', fit);
poll();
