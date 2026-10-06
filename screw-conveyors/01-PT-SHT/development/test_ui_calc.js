const fs = require('fs');
const vm = require('vm');
const path = require('path');

const base = path.resolve('outputs', 'Шнек 1 — параметрическая модель');
const html = fs.readFileSync(path.join(base, 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/load\(\);\s*$/, '');
const baseline = JSON.parse(fs.readFileSync(path.join(base, 'state.json'), 'utf8')).values;
const elements = Object.fromEntries(Object.entries(baseline).map(([id, value]) => [id, {value: String(value)}]));
for (const id of ['clearance','clearanceNote','bore','fullLength','turnCount','drawingLength','helix','apply','openCad','buildDrawings','standardCheck']) {
  elements[id] = {style:{}, setAttribute() {}};
}
const context = vm.createContext({
  document: {getElementById: id => elements[id]},
  Number, Object, console, setTimeout,
});
vm.runInContext(script, context);
vm.runInContext('render()', context);
const gap = (baseline.tube_diameter - 2 * baseline.tube_wall - baseline.screw_diameter) / 2;
assert(elements.clearance.innerHTML.startsWith(gap.toLocaleString('ru-RU')), 'wrong nominal clearance');
assert(elements.bore.textContent.startsWith(String(baseline.tube_diameter - 2 * baseline.tube_wall)), 'wrong bore');
assert(elements.apply.disabled === false, 'valid model disabled');
console.log('valid', {gap, bore: elements.bore.textContent, length: elements.fullLength.textContent});

elements.tube_diameter.value = String(baseline.screw_diameter + 2 * baseline.tube_wall);
vm.runInContext('render()', context);
assert(elements.apply.disabled === true, 'interference should disable Apply');
console.log('interference', {gap: elements.clearance.innerHTML, disabled: elements.apply.disabled});

function assert(condition, message) { if (!condition) throw Error(message); }
