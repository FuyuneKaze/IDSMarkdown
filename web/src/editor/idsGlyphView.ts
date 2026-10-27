/**
 * IdsGlyphNode 的 ProseMirror NodeView
 *
 * 渲染策略:
 *   1. PUA 码点已分配 + 字体就绪 → 渲染 PUA 字符 (选中表现与普通文字一致)
 *   2. 有 SVG 数据 → 用 <img> 渲染 (字体未就绪时的兜底)
 *   3. 无 SVG → 占位符 [idsSource]
 */
import type { NodeView } from "@tiptap/pm/view";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { glyphFontManager } from "./glyphFontManager";

export class IdsGlyphNodeView implements NodeView {
  dom: HTMLElement;

  constructor(node: ProseMirrorNode, _view?: unknown, _getPos?: unknown, _decos?: unknown, _innerDeco?: unknown) {
    this.dom = document.createElement("span");
    this.dom.className = "ids-glyph";
    this._wasFontReady = glyphFontManager.ready;
    this._renderContent(node);
  }

  update(node: ProseMirrorNode): boolean {
    const attrs = (node?.attrs || {}) as Record<string, any>;
    const puaChanged = attrs.pua !== this._lastPua;
    const svgChanged = attrs.svgData !== this._lastSvgData;
    const fontNowReady = glyphFontManager.ready && !this._wasFontReady;

    if (puaChanged || svgChanged || fontNowReady) {
      this._renderContent(node);
    }

    this._lastSvgData = attrs.svgData || "";
    this._lastPua = attrs.pua ?? -1;
    this._wasFontReady = glyphFontManager.ready;
    return true;
  }

  destroy(): void { /* nothing */ }

  ignoreMutation(): boolean { return true; }

  // --- private ---

  private _lastSvgData: string = "";
  private _lastPua: number = -1;
  private _wasFontReady: boolean = false;

  private _renderContent(node: ProseMirrorNode): void {
    this.dom.innerHTML = "";

    const attrs = (node?.attrs || {}) as Record<string, any>;
    const svgData: string = attrs.svgData || "";
    const idsSource: string = attrs.idsSource || "";
    const pua: number = attrs.pua ?? -1;

    // 策略1: PUA 字符 (字体就绪时)
    if (pua > 0 && glyphFontManager.ready) {
      this.dom.setAttribute("data-pua", String(pua));
      this.dom.style.fontFamily = `IDSGlyphFont, "IDSGlyphFont-fallback"`;
      this.dom.textContent = String.fromCodePoint(pua);
      if (idsSource) this.dom.title = idsSource;
      return;
    }

    // 策略2: <img> 回退 (字体未就绪, 但 PUA 已分配时记录 data-pua 供后续 DOM 更新)
    if (pua > 0) {
      this.dom.setAttribute("data-pua", String(pua));
    }
    this.dom.style.fontFamily = "";
    if (svgData) {
      const img = document.createElement("img");
      img.src = `data:image/svg+xml,${encodeURIComponent(svgData)}`;
      img.className = "ids-glyph-img";
      img.draggable = false;
      if (idsSource) img.title = idsSource;
      this.dom.appendChild(img);
    } else {
      this.dom.className += " ids-glyph-placeholder";
      this.dom.textContent = `[${idsSource || "?"}]`;
      if (idsSource) this.dom.title = idsSource;
    }
  }
}
