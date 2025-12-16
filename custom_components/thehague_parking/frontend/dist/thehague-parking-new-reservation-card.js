var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __decorateClass = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc(target, key) : target;
  for (var i5 = decorators.length - 1, decorator; i5 >= 0; i5--)
    if (decorator = decorators[i5])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp(target, key, result);
  return result;
};

// node_modules/@lit/reactive-element/css-tag.js
var t = globalThis;
var e = t.ShadowRoot && (void 0 === t.ShadyCSS || t.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype;
var s = /* @__PURE__ */ Symbol();
var o = /* @__PURE__ */ new WeakMap();
var n = class {
  constructor(t4, e5, o6) {
    if (this._$cssResult$ = true, o6 !== s) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t4, this.t = e5;
  }
  get styleSheet() {
    let t4 = this.o;
    const s4 = this.t;
    if (e && void 0 === t4) {
      const e5 = void 0 !== s4 && 1 === s4.length;
      e5 && (t4 = o.get(s4)), void 0 === t4 && ((this.o = t4 = new CSSStyleSheet()).replaceSync(this.cssText), e5 && o.set(s4, t4));
    }
    return t4;
  }
  toString() {
    return this.cssText;
  }
};
var r = (t4) => new n("string" == typeof t4 ? t4 : t4 + "", void 0, s);
var i = (t4, ...e5) => {
  const o6 = 1 === t4.length ? t4[0] : e5.reduce(((e6, s4, o7) => e6 + ((t5) => {
    if (true === t5._$cssResult$) return t5.cssText;
    if ("number" == typeof t5) return t5;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + t5 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s4) + t4[o7 + 1]), t4[0]);
  return new n(o6, t4, s);
};
var S = (s4, o6) => {
  if (e) s4.adoptedStyleSheets = o6.map(((t4) => t4 instanceof CSSStyleSheet ? t4 : t4.styleSheet));
  else for (const e5 of o6) {
    const o7 = document.createElement("style"), n5 = t.litNonce;
    void 0 !== n5 && o7.setAttribute("nonce", n5), o7.textContent = e5.cssText, s4.appendChild(o7);
  }
};
var c = e ? (t4) => t4 : (t4) => t4 instanceof CSSStyleSheet ? ((t5) => {
  let e5 = "";
  for (const s4 of t5.cssRules) e5 += s4.cssText;
  return r(e5);
})(t4) : t4;

// node_modules/@lit/reactive-element/reactive-element.js
var { is: i2, defineProperty: e2, getOwnPropertyDescriptor: h, getOwnPropertyNames: r2, getOwnPropertySymbols: o2, getPrototypeOf: n2 } = Object;
var a = globalThis;
var c2 = a.trustedTypes;
var l = c2 ? c2.emptyScript : "";
var p = a.reactiveElementPolyfillSupport;
var d = (t4, s4) => t4;
var u = { toAttribute(t4, s4) {
  switch (s4) {
    case Boolean:
      t4 = t4 ? l : null;
      break;
    case Object:
    case Array:
      t4 = null == t4 ? t4 : JSON.stringify(t4);
  }
  return t4;
}, fromAttribute(t4, s4) {
  let i5 = t4;
  switch (s4) {
    case Boolean:
      i5 = null !== t4;
      break;
    case Number:
      i5 = null === t4 ? null : Number(t4);
      break;
    case Object:
    case Array:
      try {
        i5 = JSON.parse(t4);
      } catch (t5) {
        i5 = null;
      }
  }
  return i5;
} };
var f = (t4, s4) => !i2(t4, s4);
var b = { attribute: true, type: String, converter: u, reflect: false, useDefault: false, hasChanged: f };
Symbol.metadata ??= /* @__PURE__ */ Symbol("metadata"), a.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var y = class extends HTMLElement {
  static addInitializer(t4) {
    this._$Ei(), (this.l ??= []).push(t4);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t4, s4 = b) {
    if (s4.state && (s4.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t4) && ((s4 = Object.create(s4)).wrapped = true), this.elementProperties.set(t4, s4), !s4.noAccessor) {
      const i5 = /* @__PURE__ */ Symbol(), h3 = this.getPropertyDescriptor(t4, i5, s4);
      void 0 !== h3 && e2(this.prototype, t4, h3);
    }
  }
  static getPropertyDescriptor(t4, s4, i5) {
    const { get: e5, set: r6 } = h(this.prototype, t4) ?? { get() {
      return this[s4];
    }, set(t5) {
      this[s4] = t5;
    } };
    return { get: e5, set(s5) {
      const h3 = e5?.call(this);
      r6?.call(this, s5), this.requestUpdate(t4, h3, i5);
    }, configurable: true, enumerable: true };
  }
  static getPropertyOptions(t4) {
    return this.elementProperties.get(t4) ?? b;
  }
  static _$Ei() {
    if (this.hasOwnProperty(d("elementProperties"))) return;
    const t4 = n2(this);
    t4.finalize(), void 0 !== t4.l && (this.l = [...t4.l]), this.elementProperties = new Map(t4.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(d("finalized"))) return;
    if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d("properties"))) {
      const t5 = this.properties, s4 = [...r2(t5), ...o2(t5)];
      for (const i5 of s4) this.createProperty(i5, t5[i5]);
    }
    const t4 = this[Symbol.metadata];
    if (null !== t4) {
      const s4 = litPropertyMetadata.get(t4);
      if (void 0 !== s4) for (const [t5, i5] of s4) this.elementProperties.set(t5, i5);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t5, s4] of this.elementProperties) {
      const i5 = this._$Eu(t5, s4);
      void 0 !== i5 && this._$Eh.set(i5, t5);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(s4) {
    const i5 = [];
    if (Array.isArray(s4)) {
      const e5 = new Set(s4.flat(1 / 0).reverse());
      for (const s5 of e5) i5.unshift(c(s5));
    } else void 0 !== s4 && i5.push(c(s4));
    return i5;
  }
  static _$Eu(t4, s4) {
    const i5 = s4.attribute;
    return false === i5 ? void 0 : "string" == typeof i5 ? i5 : "string" == typeof t4 ? t4.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise(((t4) => this.enableUpdating = t4)), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach(((t4) => t4(this)));
  }
  addController(t4) {
    (this._$EO ??= /* @__PURE__ */ new Set()).add(t4), void 0 !== this.renderRoot && this.isConnected && t4.hostConnected?.();
  }
  removeController(t4) {
    this._$EO?.delete(t4);
  }
  _$E_() {
    const t4 = /* @__PURE__ */ new Map(), s4 = this.constructor.elementProperties;
    for (const i5 of s4.keys()) this.hasOwnProperty(i5) && (t4.set(i5, this[i5]), delete this[i5]);
    t4.size > 0 && (this._$Ep = t4);
  }
  createRenderRoot() {
    const t4 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return S(t4, this.constructor.elementStyles), t4;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(true), this._$EO?.forEach(((t4) => t4.hostConnected?.()));
  }
  enableUpdating(t4) {
  }
  disconnectedCallback() {
    this._$EO?.forEach(((t4) => t4.hostDisconnected?.()));
  }
  attributeChangedCallback(t4, s4, i5) {
    this._$AK(t4, i5);
  }
  _$ET(t4, s4) {
    const i5 = this.constructor.elementProperties.get(t4), e5 = this.constructor._$Eu(t4, i5);
    if (void 0 !== e5 && true === i5.reflect) {
      const h3 = (void 0 !== i5.converter?.toAttribute ? i5.converter : u).toAttribute(s4, i5.type);
      this._$Em = t4, null == h3 ? this.removeAttribute(e5) : this.setAttribute(e5, h3), this._$Em = null;
    }
  }
  _$AK(t4, s4) {
    const i5 = this.constructor, e5 = i5._$Eh.get(t4);
    if (void 0 !== e5 && this._$Em !== e5) {
      const t5 = i5.getPropertyOptions(e5), h3 = "function" == typeof t5.converter ? { fromAttribute: t5.converter } : void 0 !== t5.converter?.fromAttribute ? t5.converter : u;
      this._$Em = e5;
      const r6 = h3.fromAttribute(s4, t5.type);
      this[e5] = r6 ?? this._$Ej?.get(e5) ?? r6, this._$Em = null;
    }
  }
  requestUpdate(t4, s4, i5) {
    if (void 0 !== t4) {
      const e5 = this.constructor, h3 = this[t4];
      if (i5 ??= e5.getPropertyOptions(t4), !((i5.hasChanged ?? f)(h3, s4) || i5.useDefault && i5.reflect && h3 === this._$Ej?.get(t4) && !this.hasAttribute(e5._$Eu(t4, i5)))) return;
      this.C(t4, s4, i5);
    }
    false === this.isUpdatePending && (this._$ES = this._$EP());
  }
  C(t4, s4, { useDefault: i5, reflect: e5, wrapped: h3 }, r6) {
    i5 && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(t4) && (this._$Ej.set(t4, r6 ?? s4 ?? this[t4]), true !== h3 || void 0 !== r6) || (this._$AL.has(t4) || (this.hasUpdated || i5 || (s4 = void 0), this._$AL.set(t4, s4)), true === e5 && this._$Em !== t4 && (this._$Eq ??= /* @__PURE__ */ new Set()).add(t4));
  }
  async _$EP() {
    this.isUpdatePending = true;
    try {
      await this._$ES;
    } catch (t5) {
      Promise.reject(t5);
    }
    const t4 = this.scheduleUpdate();
    return null != t4 && await t4, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [t6, s5] of this._$Ep) this[t6] = s5;
        this._$Ep = void 0;
      }
      const t5 = this.constructor.elementProperties;
      if (t5.size > 0) for (const [s5, i5] of t5) {
        const { wrapped: t6 } = i5, e5 = this[s5];
        true !== t6 || this._$AL.has(s5) || void 0 === e5 || this.C(s5, void 0, i5, e5);
      }
    }
    let t4 = false;
    const s4 = this._$AL;
    try {
      t4 = this.shouldUpdate(s4), t4 ? (this.willUpdate(s4), this._$EO?.forEach(((t5) => t5.hostUpdate?.())), this.update(s4)) : this._$EM();
    } catch (s5) {
      throw t4 = false, this._$EM(), s5;
    }
    t4 && this._$AE(s4);
  }
  willUpdate(t4) {
  }
  _$AE(t4) {
    this._$EO?.forEach(((t5) => t5.hostUpdated?.())), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t4)), this.updated(t4);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = false;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t4) {
    return true;
  }
  update(t4) {
    this._$Eq &&= this._$Eq.forEach(((t5) => this._$ET(t5, this[t5]))), this._$EM();
  }
  updated(t4) {
  }
  firstUpdated(t4) {
  }
};
y.elementStyles = [], y.shadowRootOptions = { mode: "open" }, y[d("elementProperties")] = /* @__PURE__ */ new Map(), y[d("finalized")] = /* @__PURE__ */ new Map(), p?.({ ReactiveElement: y }), (a.reactiveElementVersions ??= []).push("2.1.1");

// node_modules/lit-html/lit-html.js
var t2 = globalThis;
var i3 = t2.trustedTypes;
var s2 = i3 ? i3.createPolicy("lit-html", { createHTML: (t4) => t4 }) : void 0;
var e3 = "$lit$";
var h2 = `lit$${Math.random().toFixed(9).slice(2)}$`;
var o3 = "?" + h2;
var n3 = `<${o3}>`;
var r3 = document;
var l2 = () => r3.createComment("");
var c3 = (t4) => null === t4 || "object" != typeof t4 && "function" != typeof t4;
var a2 = Array.isArray;
var u2 = (t4) => a2(t4) || "function" == typeof t4?.[Symbol.iterator];
var d2 = "[ 	\n\f\r]";
var f2 = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g;
var v = /-->/g;
var _ = />/g;
var m = RegExp(`>|${d2}(?:([^\\s"'>=/]+)(${d2}*=${d2}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g");
var p2 = /'/g;
var g = /"/g;
var $ = /^(?:script|style|textarea|title)$/i;
var y2 = (t4) => (i5, ...s4) => ({ _$litType$: t4, strings: i5, values: s4 });
var x = y2(1);
var b2 = y2(2);
var w = y2(3);
var T = /* @__PURE__ */ Symbol.for("lit-noChange");
var E = /* @__PURE__ */ Symbol.for("lit-nothing");
var A = /* @__PURE__ */ new WeakMap();
var C = r3.createTreeWalker(r3, 129);
function P(t4, i5) {
  if (!a2(t4) || !t4.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return void 0 !== s2 ? s2.createHTML(i5) : i5;
}
var V = (t4, i5) => {
  const s4 = t4.length - 1, o6 = [];
  let r6, l3 = 2 === i5 ? "<svg>" : 3 === i5 ? "<math>" : "", c4 = f2;
  for (let i6 = 0; i6 < s4; i6++) {
    const s5 = t4[i6];
    let a3, u3, d3 = -1, y3 = 0;
    for (; y3 < s5.length && (c4.lastIndex = y3, u3 = c4.exec(s5), null !== u3); ) y3 = c4.lastIndex, c4 === f2 ? "!--" === u3[1] ? c4 = v : void 0 !== u3[1] ? c4 = _ : void 0 !== u3[2] ? ($.test(u3[2]) && (r6 = RegExp("</" + u3[2], "g")), c4 = m) : void 0 !== u3[3] && (c4 = m) : c4 === m ? ">" === u3[0] ? (c4 = r6 ?? f2, d3 = -1) : void 0 === u3[1] ? d3 = -2 : (d3 = c4.lastIndex - u3[2].length, a3 = u3[1], c4 = void 0 === u3[3] ? m : '"' === u3[3] ? g : p2) : c4 === g || c4 === p2 ? c4 = m : c4 === v || c4 === _ ? c4 = f2 : (c4 = m, r6 = void 0);
    const x2 = c4 === m && t4[i6 + 1].startsWith("/>") ? " " : "";
    l3 += c4 === f2 ? s5 + n3 : d3 >= 0 ? (o6.push(a3), s5.slice(0, d3) + e3 + s5.slice(d3) + h2 + x2) : s5 + h2 + (-2 === d3 ? i6 : x2);
  }
  return [P(t4, l3 + (t4[s4] || "<?>") + (2 === i5 ? "</svg>" : 3 === i5 ? "</math>" : "")), o6];
};
var N = class _N {
  constructor({ strings: t4, _$litType$: s4 }, n5) {
    let r6;
    this.parts = [];
    let c4 = 0, a3 = 0;
    const u3 = t4.length - 1, d3 = this.parts, [f3, v2] = V(t4, s4);
    if (this.el = _N.createElement(f3, n5), C.currentNode = this.el.content, 2 === s4 || 3 === s4) {
      const t5 = this.el.content.firstChild;
      t5.replaceWith(...t5.childNodes);
    }
    for (; null !== (r6 = C.nextNode()) && d3.length < u3; ) {
      if (1 === r6.nodeType) {
        if (r6.hasAttributes()) for (const t5 of r6.getAttributeNames()) if (t5.endsWith(e3)) {
          const i5 = v2[a3++], s5 = r6.getAttribute(t5).split(h2), e5 = /([.?@])?(.*)/.exec(i5);
          d3.push({ type: 1, index: c4, name: e5[2], strings: s5, ctor: "." === e5[1] ? H : "?" === e5[1] ? I : "@" === e5[1] ? L : k }), r6.removeAttribute(t5);
        } else t5.startsWith(h2) && (d3.push({ type: 6, index: c4 }), r6.removeAttribute(t5));
        if ($.test(r6.tagName)) {
          const t5 = r6.textContent.split(h2), s5 = t5.length - 1;
          if (s5 > 0) {
            r6.textContent = i3 ? i3.emptyScript : "";
            for (let i5 = 0; i5 < s5; i5++) r6.append(t5[i5], l2()), C.nextNode(), d3.push({ type: 2, index: ++c4 });
            r6.append(t5[s5], l2());
          }
        }
      } else if (8 === r6.nodeType) if (r6.data === o3) d3.push({ type: 2, index: c4 });
      else {
        let t5 = -1;
        for (; -1 !== (t5 = r6.data.indexOf(h2, t5 + 1)); ) d3.push({ type: 7, index: c4 }), t5 += h2.length - 1;
      }
      c4++;
    }
  }
  static createElement(t4, i5) {
    const s4 = r3.createElement("template");
    return s4.innerHTML = t4, s4;
  }
};
function S2(t4, i5, s4 = t4, e5) {
  if (i5 === T) return i5;
  let h3 = void 0 !== e5 ? s4._$Co?.[e5] : s4._$Cl;
  const o6 = c3(i5) ? void 0 : i5._$litDirective$;
  return h3?.constructor !== o6 && (h3?._$AO?.(false), void 0 === o6 ? h3 = void 0 : (h3 = new o6(t4), h3._$AT(t4, s4, e5)), void 0 !== e5 ? (s4._$Co ??= [])[e5] = h3 : s4._$Cl = h3), void 0 !== h3 && (i5 = S2(t4, h3._$AS(t4, i5.values), h3, e5)), i5;
}
var M = class {
  constructor(t4, i5) {
    this._$AV = [], this._$AN = void 0, this._$AD = t4, this._$AM = i5;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t4) {
    const { el: { content: i5 }, parts: s4 } = this._$AD, e5 = (t4?.creationScope ?? r3).importNode(i5, true);
    C.currentNode = e5;
    let h3 = C.nextNode(), o6 = 0, n5 = 0, l3 = s4[0];
    for (; void 0 !== l3; ) {
      if (o6 === l3.index) {
        let i6;
        2 === l3.type ? i6 = new R(h3, h3.nextSibling, this, t4) : 1 === l3.type ? i6 = new l3.ctor(h3, l3.name, l3.strings, this, t4) : 6 === l3.type && (i6 = new z(h3, this, t4)), this._$AV.push(i6), l3 = s4[++n5];
      }
      o6 !== l3?.index && (h3 = C.nextNode(), o6++);
    }
    return C.currentNode = r3, e5;
  }
  p(t4) {
    let i5 = 0;
    for (const s4 of this._$AV) void 0 !== s4 && (void 0 !== s4.strings ? (s4._$AI(t4, s4, i5), i5 += s4.strings.length - 2) : s4._$AI(t4[i5])), i5++;
  }
};
var R = class _R {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(t4, i5, s4, e5) {
    this.type = 2, this._$AH = E, this._$AN = void 0, this._$AA = t4, this._$AB = i5, this._$AM = s4, this.options = e5, this._$Cv = e5?.isConnected ?? true;
  }
  get parentNode() {
    let t4 = this._$AA.parentNode;
    const i5 = this._$AM;
    return void 0 !== i5 && 11 === t4?.nodeType && (t4 = i5.parentNode), t4;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t4, i5 = this) {
    t4 = S2(this, t4, i5), c3(t4) ? t4 === E || null == t4 || "" === t4 ? (this._$AH !== E && this._$AR(), this._$AH = E) : t4 !== this._$AH && t4 !== T && this._(t4) : void 0 !== t4._$litType$ ? this.$(t4) : void 0 !== t4.nodeType ? this.T(t4) : u2(t4) ? this.k(t4) : this._(t4);
  }
  O(t4) {
    return this._$AA.parentNode.insertBefore(t4, this._$AB);
  }
  T(t4) {
    this._$AH !== t4 && (this._$AR(), this._$AH = this.O(t4));
  }
  _(t4) {
    this._$AH !== E && c3(this._$AH) ? this._$AA.nextSibling.data = t4 : this.T(r3.createTextNode(t4)), this._$AH = t4;
  }
  $(t4) {
    const { values: i5, _$litType$: s4 } = t4, e5 = "number" == typeof s4 ? this._$AC(t4) : (void 0 === s4.el && (s4.el = N.createElement(P(s4.h, s4.h[0]), this.options)), s4);
    if (this._$AH?._$AD === e5) this._$AH.p(i5);
    else {
      const t5 = new M(e5, this), s5 = t5.u(this.options);
      t5.p(i5), this.T(s5), this._$AH = t5;
    }
  }
  _$AC(t4) {
    let i5 = A.get(t4.strings);
    return void 0 === i5 && A.set(t4.strings, i5 = new N(t4)), i5;
  }
  k(t4) {
    a2(this._$AH) || (this._$AH = [], this._$AR());
    const i5 = this._$AH;
    let s4, e5 = 0;
    for (const h3 of t4) e5 === i5.length ? i5.push(s4 = new _R(this.O(l2()), this.O(l2()), this, this.options)) : s4 = i5[e5], s4._$AI(h3), e5++;
    e5 < i5.length && (this._$AR(s4 && s4._$AB.nextSibling, e5), i5.length = e5);
  }
  _$AR(t4 = this._$AA.nextSibling, i5) {
    for (this._$AP?.(false, true, i5); t4 !== this._$AB; ) {
      const i6 = t4.nextSibling;
      t4.remove(), t4 = i6;
    }
  }
  setConnected(t4) {
    void 0 === this._$AM && (this._$Cv = t4, this._$AP?.(t4));
  }
};
var k = class {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t4, i5, s4, e5, h3) {
    this.type = 1, this._$AH = E, this._$AN = void 0, this.element = t4, this.name = i5, this._$AM = e5, this.options = h3, s4.length > 2 || "" !== s4[0] || "" !== s4[1] ? (this._$AH = Array(s4.length - 1).fill(new String()), this.strings = s4) : this._$AH = E;
  }
  _$AI(t4, i5 = this, s4, e5) {
    const h3 = this.strings;
    let o6 = false;
    if (void 0 === h3) t4 = S2(this, t4, i5, 0), o6 = !c3(t4) || t4 !== this._$AH && t4 !== T, o6 && (this._$AH = t4);
    else {
      const e6 = t4;
      let n5, r6;
      for (t4 = h3[0], n5 = 0; n5 < h3.length - 1; n5++) r6 = S2(this, e6[s4 + n5], i5, n5), r6 === T && (r6 = this._$AH[n5]), o6 ||= !c3(r6) || r6 !== this._$AH[n5], r6 === E ? t4 = E : t4 !== E && (t4 += (r6 ?? "") + h3[n5 + 1]), this._$AH[n5] = r6;
    }
    o6 && !e5 && this.j(t4);
  }
  j(t4) {
    t4 === E ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t4 ?? "");
  }
};
var H = class extends k {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t4) {
    this.element[this.name] = t4 === E ? void 0 : t4;
  }
};
var I = class extends k {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t4) {
    this.element.toggleAttribute(this.name, !!t4 && t4 !== E);
  }
};
var L = class extends k {
  constructor(t4, i5, s4, e5, h3) {
    super(t4, i5, s4, e5, h3), this.type = 5;
  }
  _$AI(t4, i5 = this) {
    if ((t4 = S2(this, t4, i5, 0) ?? E) === T) return;
    const s4 = this._$AH, e5 = t4 === E && s4 !== E || t4.capture !== s4.capture || t4.once !== s4.once || t4.passive !== s4.passive, h3 = t4 !== E && (s4 === E || e5);
    e5 && this.element.removeEventListener(this.name, this, s4), h3 && this.element.addEventListener(this.name, this, t4), this._$AH = t4;
  }
  handleEvent(t4) {
    "function" == typeof this._$AH ? this._$AH.call(this.options?.host ?? this.element, t4) : this._$AH.handleEvent(t4);
  }
};
var z = class {
  constructor(t4, i5, s4) {
    this.element = t4, this.type = 6, this._$AN = void 0, this._$AM = i5, this.options = s4;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t4) {
    S2(this, t4);
  }
};
var j = t2.litHtmlPolyfillSupport;
j?.(N, R), (t2.litHtmlVersions ??= []).push("3.3.1");
var B = (t4, i5, s4) => {
  const e5 = s4?.renderBefore ?? i5;
  let h3 = e5._$litPart$;
  if (void 0 === h3) {
    const t5 = s4?.renderBefore ?? null;
    e5._$litPart$ = h3 = new R(i5.insertBefore(l2(), t5), t5, void 0, s4 ?? {});
  }
  return h3._$AI(t4), h3;
};

// node_modules/lit-element/lit-element.js
var s3 = globalThis;
var i4 = class extends y {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    const t4 = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= t4.firstChild, t4;
  }
  update(t4) {
    const r6 = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t4), this._$Do = B(r6, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(true);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(false);
  }
  render() {
    return T;
  }
};
i4._$litElement$ = true, i4["finalized"] = true, s3.litElementHydrateSupport?.({ LitElement: i4 });
var o4 = s3.litElementPolyfillSupport;
o4?.({ LitElement: i4 });
(s3.litElementVersions ??= []).push("4.2.1");

// node_modules/@lit/reactive-element/decorators/custom-element.js
var t3 = (t4) => (e5, o6) => {
  void 0 !== o6 ? o6.addInitializer((() => {
    customElements.define(t4, e5);
  })) : customElements.define(t4, e5);
};

// node_modules/@lit/reactive-element/decorators/property.js
var o5 = { attribute: true, type: String, converter: u, reflect: false, hasChanged: f };
var r4 = (t4 = o5, e5, r6) => {
  const { kind: n5, metadata: i5 } = r6;
  let s4 = globalThis.litPropertyMetadata.get(i5);
  if (void 0 === s4 && globalThis.litPropertyMetadata.set(i5, s4 = /* @__PURE__ */ new Map()), "setter" === n5 && ((t4 = Object.create(t4)).wrapped = true), s4.set(r6.name, t4), "accessor" === n5) {
    const { name: o6 } = r6;
    return { set(r7) {
      const n6 = e5.get.call(this);
      e5.set.call(this, r7), this.requestUpdate(o6, n6, t4);
    }, init(e6) {
      return void 0 !== e6 && this.C(o6, void 0, t4, e6), e6;
    } };
  }
  if ("setter" === n5) {
    const { name: o6 } = r6;
    return function(r7) {
      const n6 = this[o6];
      e5.call(this, r7), this.requestUpdate(o6, n6, t4);
    };
  }
  throw Error("Unsupported decorator location: " + n5);
};
function n4(t4) {
  return (e5, o6) => "object" == typeof o6 ? r4(t4, e5, o6) : ((t5, e6, o7) => {
    const r6 = e6.hasOwnProperty(o7);
    return e6.constructor.createProperty(o7, t5), r6 ? Object.getOwnPropertyDescriptor(e6, o7) : void 0;
  })(t4, e5, o6);
}

// node_modules/@lit/reactive-element/decorators/state.js
function r5(r6) {
  return n4({ ...r6, state: true, attribute: false });
}

// translations/en.json
var en_default = {
  common: {
    working: "Working\u2026",
    dash: "\u2014"
  },
  active_reservation_card: {
    card_name: "The Hague parking",
    card_description: "Show active reservations and end them.",
    default_title: "The Hague parking",
    service: "Service",
    meldnummer: "Registration number",
    title: "Title (optional)",
    reservations_sensor: "Reservations sensor",
    set_entity_error: "Set `entity` to the `reservations` sensor",
    entity_not_found: "Entity not found: {entity}",
    no_active_reservations: "No active reservations",
    reservation_fallback_label: "Reservation",
    adjust: "Adjust",
    end: "End",
    reservation_id_missing: "Reservation ID is missing",
    invalid_reservation_id: "Invalid reservation ID",
    pick_new_end_time: "Select a new end time first",
    invalid_end_time: "Invalid end time",
    end_time_after_start: "End time must be after start time",
    end_time_unchanged: "End time is unchanged",
    could_not_adjust_end_time: "Could not adjust the reservation end time"
  },
  new_reservation_card: {
    card_name: "The Hague parking - new reservation",
    card_description: "Create a new reservation with favorites support.",
    default_title: "New reservation",
    set_meldnummer_error: "Select a `service` in the editor, or set `config_entry_id` manually. Alternatively, set `entity: sensor.thehague_parking_*_reservations` or `favorites_entity: sensor.thehague_parking_*_favorieten`.",
    missing_favorites_warning: "No favorites found. Select a `service`, or set `favorites_entity: sensor.thehague_parking_*_favorieten` manually to show favorites.",
    service: "Service",
    meldnummer: "Registration number",
    reservations_sensor: "Reservations sensor (optional)",
    favorites_sensor: "Favorites sensor (optional)",
    favorites: "Favorites",
    name: "Name",
    license_plate_required: "License plate (required)",
    add_to_favorites: "Add to favorites",
    submit: "Submit",
    license_plate_required_error: "Enter a license plate",
    favorite_name_required_error: "Enter a name to save the favorite",
    could_not_save_favorite: "Could not save favorite",
    could_not_submit: "Could not submit the reservation"
  }
};

// translations/nl.json
var nl_default = {
  common: {
    working: "Bezig\u2026",
    dash: "\u2014"
  },
  active_reservation_card: {
    card_name: "Den Haag parkeren",
    card_description: "Toon actieve reserveringen en be\xEBindig ze.",
    default_title: "Den Haag parkeren",
    service: "Dienst",
    meldnummer: "Meldnummer",
    title: "Titel (optioneel)",
    reservations_sensor: "Reserveringen sensor",
    set_entity_error: "Stel `entity` in op de `reservations` sensor",
    entity_not_found: "Entiteit niet gevonden: {entity}",
    no_active_reservations: "Geen actieve reserveringen",
    reservation_fallback_label: "Reservering",
    adjust: "Aanpassen",
    end: "Be\xEBindigen",
    reservation_id_missing: "Reservatie-id ontbreekt",
    invalid_reservation_id: "Ongeldige reservatie-id",
    pick_new_end_time: "Kies eerst een nieuwe eindtijd",
    invalid_end_time: "Ongeldige eindtijd",
    end_time_after_start: "Eindtijd moet na starttijd liggen",
    end_time_unchanged: "Eindtijd is ongewijzigd",
    could_not_adjust_end_time: "Kon de eindtijd van de reservatie niet aanpassen"
  },
  new_reservation_card: {
    card_name: "Den Haag parkeren - nieuwe reservering",
    card_description: "Maak een nieuwe reservering met favorieten.",
    default_title: "Nieuwe reservering",
    set_meldnummer_error: "Selecteer een `dienst` in de editor, of stel handmatig `config_entry_id` in. Als alternatief kun je `entity: sensor.thehague_parking_*_reservations` of `favorites_entity: sensor.thehague_parking_*_favorieten` gebruiken.",
    missing_favorites_warning: "Geen favorieten gevonden. Selecteer een `dienst`, of stel `favorites_entity: sensor.thehague_parking_*_favorieten` handmatig in om favorieten te tonen.",
    service: "Dienst",
    meldnummer: "Meldnummer",
    reservations_sensor: "Reserveringen sensor (optioneel)",
    favorites_sensor: "Favorieten sensor (optioneel)",
    favorites: "Favorieten",
    name: "Naam",
    license_plate_required: "Kenteken (verplicht)",
    add_to_favorites: "Toevoegen aan favorieten",
    submit: "Aanmelden",
    license_plate_required_error: "Vul een kenteken in",
    favorite_name_required_error: "Vul een naam in om de favoriet op te slaan",
    could_not_save_favorite: "Kon favoriet niet opslaan",
    could_not_submit: "Kon de reservering niet aanmelden"
  }
};

// src/localize.ts
var TRANSLATIONS = { en: en_default, nl: nl_default };
var DEFAULT_LANGUAGE = "en";
function _deepGet(obj, path) {
  if (!obj || typeof obj !== "object") return void 0;
  let current = obj;
  for (const segment of path.split(".")) {
    if (!current || typeof current !== "object") return void 0;
    current = current[segment];
  }
  return typeof current === "string" ? current : void 0;
}
function _format(template, placeholders) {
  if (!placeholders) return template;
  return template.replaceAll(/\{(?<key>[a-zA-Z0-9_]+)\}/g, (match, key) => {
    if (!key) return match;
    return Object.prototype.hasOwnProperty.call(placeholders, key) ? placeholders[key] : match;
  });
}
function localize(hass, key, placeholders) {
  const hassObj = hass;
  return localizeLanguage(hassObj?.locale?.language, key, placeholders);
}
function localizeLanguage(language, key, placeholders) {
  const resolvedLanguage = language ?? DEFAULT_LANGUAGE;
  const table = TRANSLATIONS[resolvedLanguage] ?? TRANSLATIONS[resolvedLanguage.split("-")[0]] ?? TRANSLATIONS[DEFAULT_LANGUAGE];
  return _format(
    _deepGet(table, key) ?? _deepGet(TRANSLATIONS[DEFAULT_LANGUAGE], key) ?? key,
    placeholders
  );
}

// src/thehague-parking-new-reservation-card-editor.ts
var TheHagueParkingNewReservationCardEditor = class extends i4 {
  constructor() {
    super(...arguments);
    this._entries = [];
    this._entriesLoaded = false;
  }
  setConfig(config) {
    this._config = { ...config };
    this._selectDefaultEntryIfNeeded();
  }
  updated(changedProps) {
    if (!this.hass || this._entriesLoaded) return;
    if (changedProps.has("hass")) {
      void this._loadEntries();
    }
  }
  async _loadEntries() {
    if (!this.hass) return;
    try {
      const entries = await this.hass.callWS({
        type: "config_entries/get",
        domain: "thehague_parking"
      });
      this._entries = entries;
    } catch (_err) {
      this._entries = [];
    } finally {
      this._entriesLoaded = true;
      this._selectDefaultEntryIfNeeded();
    }
  }
  _parseMeldnummerFromTitle(title) {
    const match = /\\((?<id>[^)]+)\\)\\s*$/.exec(title);
    return match?.groups?.id?.trim() || void 0;
  }
  _selectDefaultEntryIfNeeded() {
    if (!this._config) return;
    if (!this._entriesLoaded || this._entries.length === 0) return;
    const meldnummer = (this._config.meldnummer ?? "").trim();
    const registrationNumber = (this._config.registration_number ?? "").trim();
    const slug = (this._config.slug ?? "").trim();
    const hasSelection = !!this._config.config_entry_id || !!this._config.entity || !!this._config.favorites_entity || !!meldnummer || !!registrationNumber || !!slug;
    if (hasSelection) return;
    const first = this._entries[0];
    if (!first) return;
    this._applyEntry(first.entry_id);
  }
  _applyEntry(entryId) {
    if (!this._config) return;
    const entry = entryId ? this._entries.find((e5) => e5.entry_id === entryId) : void 0;
    const meldnummer = entry ? this._parseMeldnummerFromTitle(entry.title) : void 0;
    const slug = meldnummer ?? "";
    this._config = {
      ...this._config,
      config_entry_id: entryId,
      meldnummer,
      ...slug && { entity: `sensor.thehague_parking_${slug}_reservations` },
      ...slug && { favorites_entity: `sensor.thehague_parking_${slug}_favorieten` }
    };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true
      })
    );
  }
  _entryChanged(ev) {
    this._applyEntry(ev.target.value || void 0);
  }
  _valueChanged(ev) {
    if (!this._config) return;
    const value = ev.detail.value;
    this._config = { ...this._config, entity: value };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true
      })
    );
  }
  _favoritesChanged(ev) {
    if (!this._config) return;
    const value = ev.detail.value;
    this._config = { ...this._config, favorites_entity: value };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true
      })
    );
  }
  render() {
    if (!this.hass) return E;
    return x`
      <div class="container">
        <div class="field">
          <div class="label">${localize(this.hass, "new_reservation_card.service")}</div>
          <select
            class="select"
            .value=${this._config?.config_entry_id ?? ""}
            @change=${this._entryChanged}
          >
            ${this._entries.map(
      (entry) => x`<option .value=${entry.entry_id}>${entry.title}</option>`
    )}
          </select>
        </div>

        <ha-entity-picker
          .hass=${this.hass}
          .value=${this._config?.entity ?? ""}
          .includeDomains=${["sensor"]}
          .filter=${(eid) => eid.startsWith("sensor.thehague_parking_") && eid.endsWith("_reservations")}
          label=${localize(this.hass, "new_reservation_card.reservations_sensor")}
          @value-changed=${this._valueChanged}
        ></ha-entity-picker>

        <ha-entity-picker
          .hass=${this.hass}
          .value=${this._config?.favorites_entity ?? ""}
          .includeDomains=${["sensor"]}
          .filter=${(eid) => eid.startsWith("sensor.thehague_parking_") && (eid.endsWith("_favorieten") || eid.endsWith("_favorites"))}
          label=${localize(this.hass, "new_reservation_card.favorites_sensor")}
          @value-changed=${this._favoritesChanged}
        ></ha-entity-picker>
      </div>
    `;
  }
};
TheHagueParkingNewReservationCardEditor.styles = i`
    .container {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .label {
      font-weight: 500;
    }

    .select {
      border: 1px solid var(--divider-color);
      border-radius: var(--ha-card-border-radius, 12px);
      background: transparent;
      color: var(--primary-text-color);
      padding: 10px 12px;
      min-height: 40px;
    }
  `;
__decorateClass([
  n4({ attribute: false })
], TheHagueParkingNewReservationCardEditor.prototype, "hass", 2);
__decorateClass([
  n4({ attribute: false })
], TheHagueParkingNewReservationCardEditor.prototype, "_config", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCardEditor.prototype, "_entries", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCardEditor.prototype, "_entriesLoaded", 2);
TheHagueParkingNewReservationCardEditor = __decorateClass([
  t3("thehague-parking-new-reservation-card-editor")
], TheHagueParkingNewReservationCardEditor);

// src/thehague-parking-new-reservation-card.ts
var TheHagueParkingNewReservationCard = class extends i4 {
  constructor() {
    super(...arguments);
    this._favoriteDraft = "";
    this._nameDraft = "";
    this._licensePlateDraft = "";
    this._addToFavorites = false;
    this._submitting = false;
    this._resolvingService = false;
  }
  setConfig(config) {
    this._config = config;
  }
  updated(changedProps) {
    if (!this.hass || !this._config) return;
    if (!this.hass.callWS) return;
    const entryId = this._config.config_entry_id;
    if (!entryId) return;
    if (this._config.meldnummer || this._config.registration_number || this._config.slug) {
      return;
    }
    if (this._resolvedConfigEntryId === entryId && this._resolvedMeldnummer) {
      return;
    }
    if (changedProps.has("_config") || changedProps.has("hass")) {
      void this._resolveMeldnummerFromConfigEntry(entryId);
    }
  }
  _parseMeldnummerFromTitle(title) {
    const match = /\((?<id>[^)]+)\)\s*$/.exec(title);
    return match?.groups?.id?.trim() || void 0;
  }
  async _resolveMeldnummerFromConfigEntry(entryId) {
    if (!this.hass?.callWS) return;
    this._resolvingService = true;
    try {
      const entries = await this.hass.callWS({
        type: "config_entries/get",
        domain: "thehague_parking"
      });
      const entry = entries.find((e5) => e5.entry_id === entryId);
      this._resolvedConfigEntryId = entryId;
      this._resolvedMeldnummer = entry ? this._parseMeldnummerFromTitle(entry.title) : void 0;
    } catch (_err) {
      this._resolvedConfigEntryId = entryId;
      this._resolvedMeldnummer = void 0;
    } finally {
      this._resolvingService = false;
    }
  }
  static getConfigElement() {
    return document.createElement("thehague-parking-new-reservation-card-editor");
  }
  static getStubConfig() {
    return {
      type: "custom:thehague-parking-new-reservation-card",
      meldnummer: ""
    };
  }
  getCardSize() {
    return 4;
  }
  get _slug() {
    if (!this._config) return void 0;
    if (this._config.meldnummer) return this._config.meldnummer;
    if (this._config.registration_number) return this._config.registration_number;
    if (this._config.slug) return this._config.slug;
    if (this._config.config_entry_id && this._resolvedConfigEntryId === this._config.config_entry_id && this._resolvedMeldnummer) {
      return this._resolvedMeldnummer;
    }
    if (!this._config.entity) return void 0;
    const match = /^sensor\\.thehague_parking_(?<slug>.+)_(?:active_reservations|reservations)$/.exec(
      this._config.entity
    );
    return match?.groups?.slug;
  }
  _notify(message) {
    this.dispatchEvent(
      new CustomEvent("hass-notification", {
        detail: { message },
        bubbles: true,
        composed: true
      })
    );
  }
  _getEntityId(override, fallbackSuffix) {
    if (override) return override;
    const slug = this._slug;
    return slug ? `${fallbackSuffix.replace("*", slug)}` : void 0;
  }
  get _favoritesEntityId() {
    if (this._config?.favorites_entity) {
      return this._config.favorites_entity;
    }
    const slug = this._slug;
    if (!slug) {
      return void 0;
    }
    const preferred = `sensor.thehague_parking_${slug}_favorieten`;
    const fallback = `sensor.thehague_parking_${slug}_favorites`;
    if (!this.hass) {
      return preferred;
    }
    if (this.hass.states[preferred]) return preferred;
    if (this.hass.states[fallback]) return fallback;
    return preferred;
  }
  _state(entityId) {
    return entityId && this.hass ? this.hass.states[entityId] : void 0;
  }
  get _favoritesState() {
    return this._state(this._favoritesEntityId);
  }
  get _favorites() {
    const favorites = this._favoritesState?.attributes?.favorites;
    return Array.isArray(favorites) ? favorites : [];
  }
  _favoriteLabel(favorite) {
    const name = (favorite.name ?? "").trim();
    const plate = (favorite.license_plate ?? "").trim();
    if (name && plate) return `${name} - ${plate}`;
    return name || plate || "Favoriet";
  }
  _selectFavorite(indexValue) {
    this._favoriteDraft = indexValue;
    if (!indexValue) return;
    const index = Number(indexValue);
    if (!Number.isFinite(index) || index < 0 || index >= this._favorites.length) return;
    const favorite = this._favorites[index];
    if (!favorite) return;
    this._nameDraft = (favorite.name ?? "").trim();
    this._licensePlateDraft = (favorite.license_plate ?? "").trim();
  }
  async _submit() {
    if (!this.hass || !this._config) return;
    const licensePlate = this._licensePlateDraft.trim();
    if (!licensePlate) {
      this._notify(localize(this.hass, "new_reservation_card.license_plate_required_error"));
      return;
    }
    this._submitting = true;
    try {
      await this.hass.callService("thehague_parking", "create_reservation", {
        license_plate: licensePlate,
        ...this._nameDraft.trim() && { name: this._nameDraft.trim() },
        ...this._config.config_entry_id && {
          config_entry_id: this._config.config_entry_id
        }
      });
      if (this._addToFavorites) {
        if (!this._nameDraft.trim()) {
          this._notify(localize(this.hass, "new_reservation_card.favorite_name_required_error"));
        } else {
          try {
            await this.hass.callService("thehague_parking", "create_favorite", {
              name: this._nameDraft.trim(),
              license_plate: licensePlate,
              ...this._config.config_entry_id && {
                config_entry_id: this._config.config_entry_id
              }
            });
          } catch (_err) {
            this._notify(localize(this.hass, "new_reservation_card.could_not_save_favorite"));
          }
        }
      }
      this._favoriteDraft = "";
      this._nameDraft = "";
      this._licensePlateDraft = "";
      this._addToFavorites = false;
    } catch (_err) {
      this._notify(localize(this.hass, "new_reservation_card.could_not_submit"));
    } finally {
      this._submitting = false;
    }
  }
  render() {
    if (!this.hass || !this._config) return E;
    const title = this._config.title ?? localize(this.hass, "new_reservation_card.default_title");
    if (!this._slug && !this._config.entity && !this._config.favorites_entity && !this._config.config_entry_id) {
      return x`
        <ha-card header=${title}>
          <div class="card-content">
            <div class="warning">
              ${localize(this.hass, "new_reservation_card.set_meldnummer_error")}
            </div>
          </div>
        </ha-card>
      `;
    }
    const missingFavorites = !this._favoritesEntityId;
    return x`
      <ha-card header=${title}>
        <div class="card-content">
          ${this._config.config_entry_id && this._resolvingService ? x`<div class="empty">${localize(this.hass, "common.working")}</div>` : E}
          ${missingFavorites ? x`<div class="warning">
                ${localize(this.hass, "new_reservation_card.missing_favorites_warning")}
              </div>` : E}

          <div class="field">
            <div class="label">${localize(this.hass, "new_reservation_card.favorites")}</div>
            <select
              class="select"
              .value=${this._favoriteDraft}
              ?disabled=${missingFavorites || this._submitting}
              @change=${(ev) => this._selectFavorite(ev.target.value)}
            >
              <option value="">${localize(this.hass, "common.dash")}</option>
              ${this._favorites.map(
      (favorite, index) => x`<option .value=${String(index)}>
                    ${this._favoriteLabel(favorite)}
                  </option>`
    )}
            </select>
          </div>

          <div class="field">
            <div class="label">${localize(this.hass, "new_reservation_card.name")}</div>
            <input
              class="input"
              type="text"
              .value=${this._nameDraft}
              ?disabled=${this._submitting}
              @input=${(ev) => {
      this._nameDraft = ev.target.value;
    }}
            />
          </div>

          <div class="field">
            <div class="label">
              ${localize(this.hass, "new_reservation_card.license_plate_required")}
            </div>
            <input
              class="input"
              type="text"
              required
              .value=${this._licensePlateDraft}
              ?disabled=${this._submitting}
              @input=${(ev) => {
      this._licensePlateDraft = ev.target.value;
    }}
            />
          </div>

          <div class="row">
            <label class="switch-row">
              <input
                type="checkbox"
                .checked=${this._addToFavorites}
                ?disabled=${this._submitting}
                @change=${(ev) => {
      this._addToFavorites = ev.target.checked;
    }}
              />
              <span>${localize(this.hass, "new_reservation_card.add_to_favorites")}</span>
            </label>

            <ha-button
              appearance="filled"
              .disabled=${this._submitting || !this._licensePlateDraft.trim()}
              @click=${this._submit}
            >
              ${this._submitting ? localize(this.hass, "common.working") : localize(this.hass, "new_reservation_card.submit")}
            </ha-button>
          </div>
        </div>
      </ha-card>
    `;
  }
};
TheHagueParkingNewReservationCard.styles = i`
    .card-content {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .warning {
      color: var(--error-color);
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .label {
      font-weight: 500;
    }

    .input,
    .select {
      border: 1px solid var(--divider-color);
      border-radius: var(--ha-card-border-radius, 12px);
      background: transparent;
      color: var(--primary-text-color);
      padding: 10px 12px;
      min-height: 40px;
    }

    .row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }

    .switch-row {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      min-height: 40px;
    }
  `;
__decorateClass([
  n4({ attribute: false })
], TheHagueParkingNewReservationCard.prototype, "hass", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCard.prototype, "_config", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCard.prototype, "_favoriteDraft", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCard.prototype, "_nameDraft", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCard.prototype, "_licensePlateDraft", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCard.prototype, "_addToFavorites", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCard.prototype, "_submitting", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCard.prototype, "_resolvingService", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCard.prototype, "_resolvedConfigEntryId", 2);
__decorateClass([
  r5()
], TheHagueParkingNewReservationCard.prototype, "_resolvedMeldnummer", 2);
TheHagueParkingNewReservationCard = __decorateClass([
  t3("thehague-parking-new-reservation-card")
], TheHagueParkingNewReservationCard);
window.customCards ??= [];
window.customCards.push({
  type: "thehague-parking-new-reservation-card",
  name: localizeLanguage(
    globalThis.navigator?.language,
    "new_reservation_card.card_name"
  ),
  description: localizeLanguage(
    globalThis.navigator?.language,
    "new_reservation_card.card_description"
  ),
  editor: "thehague-parking-new-reservation-card-editor"
});
export {
  TheHagueParkingNewReservationCard
};
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
@lit/reactive-element/decorators/custom-element.js:
@lit/reactive-element/decorators/property.js:
@lit/reactive-element/decorators/state.js:
@lit/reactive-element/decorators/event-options.js:
@lit/reactive-element/decorators/base.js:
@lit/reactive-element/decorators/query.js:
@lit/reactive-element/decorators/query-all.js:
@lit/reactive-element/decorators/query-async.js:
@lit/reactive-element/decorators/query-assigned-nodes.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/query-assigned-elements.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
