/**
 * 统一字符分类工具 — 从 C++ Document.cpp 移植
 */

export function codePointAt(s: string, pos: number): number {
  if (pos >= s.length) return 0;
  const cp = s.charCodeAt(pos);
  if (cp >= 0xd800 && cp <= 0xdbff && pos + 1 < s.length) {
    const low = s.charCodeAt(pos + 1);
    if (low >= 0xdc00 && low <= 0xdfff)
      return 0x10000 + (cp - 0xd800) * 0x400 + (low - 0xdc00);
  }
  return cp;
}

export function cpLen(cp: number): number {
  return cp >= 0x10000 ? 2 : 1;
}

export function isIdeographic(cp: number): boolean {
  if (cp >= 0x2e80 && cp <= 0x2ef3) return true; // CJK Radicals Supplement
  if (cp >= 0x2f00 && cp <= 0x2fd5) return true; // Kangxi Radicals
  if (cp >= 0x31c0 && cp <= 0x31e3) return true; // CJK Strokes
  if (cp >= 0x2ff0 && cp <= 0x2fff) return true; // IDS Operators
  if (cp >= 0xE000 && cp <= 0xE8FF) return true; // PUA (IDS glyph font)
  if (cp >= 0x4e00 && cp <= 0x9fff) return true; // CJK Unified
  if (cp >= 0x3400 && cp <= 0x4dbf) return true; // CJK Ext A
  if (cp >= 0xf900 && cp <= 0xfaff) return true; // CJK Compat
  if (cp >= 0x17000 && cp <= 0x187f7) return true; // Tangut
  if (cp >= 0x18800 && cp <= 0x18aff) return true; // Tangut Components
  if (cp >= 0x20000 && cp <= 0x2ebe0) return true; // CJK Ext B~F
  if (cp >= 0x2f800 && cp <= 0x2fa1f) return true; // CJK Compat Sup
  if (cp >= 0x30000 && cp <= 0x323af) return true; // CJK Ext G~H
  return false;
}

export function isIdsOperator(cp: number): boolean {
  return (cp >= 0x2ff0 && cp <= 0x2fff) || cp === 0x31ef;
}

export function idsOperatorArity(cp: number): number {
  if (cp === 0x2ff2 || cp === 0x2ff3) return 3; // ⿲ ⿳
  if (cp === 0x2ffe || cp === 0x2fff) return 1; // ⿾ ⿿ (mirror, rotate)
  return 2;
}

// Surround operators: outer child encloses inner child
export const SURROUND_OPS = new Set([
  0x2ff4, 0x2ff5, 0x2ff6, 0x2ff7, 0x2ff8, 0x2ff9, 0x2ffa, 0x2ffc,
]);

export function isSurroundOp(cp: number): boolean {
  return SURROUND_OPS.has(cp);
}
