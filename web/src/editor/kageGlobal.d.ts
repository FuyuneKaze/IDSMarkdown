/** kage-bundle.js 全局函数类型声明 */

declare function loadGlyph(name: string, data: string): void;
declare function renderGlyph(name: string, curve?: boolean): string;
declare function clearGlyphs(): void;
declare function getGlyphBox(name: string): {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
} | null;
declare function getGlyphData(name: string): string;
