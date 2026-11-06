// The SUNMI T2s counter terminal runs Chromium 81 and can't be updated. It ignores inset, inset-inline-* and
// flexbox gap, which put the order panel on top of the menu. These extra rules only matter on engines like that.
const SIDES = { 'inset-inline-start': 'left', 'inset-inline-end': 'right' };

export default function oldWebview() {
  return {
    postcssPlugin: 'old-webview',
    OnceExit(root) {
      // One :where() makes that engine drop the whole rule, including Tailwind's button reset.
      root.walkRules(/:where\(/, (rule) => {
        rule.selector = rule.selector.replace(/:where\(([^()]*)\)/g, '$1');
      });
      root.walkDecls((decl) => {
        const rule = decl.parent;
        if (rule.type !== 'rule') return;
        if (decl.prop === 'inset') {
          const [top, right = top, bottom = top, left = right] = decl.value.split(/\s+/);
          Object.entries({ top, right, bottom, left }).forEach(([prop, value]) => decl.cloneBefore({ prop, value }));
        } else if (SIDES[decl.prop]) {
          const added = rule.clone({ selectors: rule.selectors.map((s) => `html[dir="ltr"] ${s}`) });
          added.removeAll();
          added.append({ prop: SIDES[decl.prop], value: decl.value });
          rule.after(added);
        } else if (decl.prop === 'gap' && /^\.gap-/.test(rule.selector)) {
          // main.tsx's old-webview import adds no-flex-gap on engines without flexbox gap.
          const row = rule.clone({ selector: `.no-flex-gap ${rule.selector}.flex > * + *` });
          row.removeAll();
          row.append({ prop: 'margin-left', value: decl.value });
          const column = rule.clone({ selector: `.no-flex-gap ${rule.selector}.flex-col > * + *` });
          column.removeAll();
          column.append({ prop: 'margin-left', value: '0' }, { prop: 'margin-top', value: decl.value });
          rule.after(column);
          rule.after(row);
        }
      });
    },
  };
}
oldWebview.postcss = true;
