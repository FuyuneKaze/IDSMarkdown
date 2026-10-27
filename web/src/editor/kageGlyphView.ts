/**
 * KageGlyphNode 的 ProseMirror NodeView — 内联 KAGE 笔画数据字形渲染
 */
import type { NodeView } from "@tiptap/pm/view";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";

export class KageGlyphNodeView implements NodeView {
  dom: HTMLElement;

  constructor(node: ProseMirrorNode, _view?: unknown, _getPos?: unknown, _decos?: unknown, _innerDeco?: unknown) {
    this.dom = document.createElement("span");
    this.dom.className = "ids-glyph";
    this._renderContent(node);
  }

  update(node: ProseMirrorNode): boolean {
    const attrs = node?.attrs || {} as Record<string, string>;
    if (attrs.svgData !== this._lastSvgData) {
      this._renderContent(node);
    }
    this._lastSvgData = attrs.svgData || "";
    return true;
  }

  destroy(): void { /* nothing */ }

  ignoreMutation(): boolean { return true; }

  // --- private ---

  private _lastSvgData: string = "";

  private _renderContent(node: ProseMirrorNode): void {
    this.dom.innerHTML = "";

    const attrs = (node?.attrs || {}) as Record<string, string>;
    const svgData: string = attrs.svgData || "";
    const glyphName: string = attrs.glyphName || "";

    if (svgData) {
      const img = document.createElement("img");
      img.src = `data:image/svg+xml,${encodeURIComponent(svgData)}`;
      img.className = "ids-glyph-img";
      img.draggable = false;
      if (glyphName) img.title = glyphName;
      this.dom.appendChild(img);
    } else {
      this.dom.className += " ids-glyph-placeholder";
      this.dom.textContent = glyphName ? `[${glyphName}]` : "[KAGE]";
      if (glyphName) this.dom.title = glyphName;
    }
  }
}
