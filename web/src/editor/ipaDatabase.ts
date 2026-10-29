import { assetUrl } from "./assetUrl";
// IPA 数据库: 加载 data/ipa_keymap.json, Alt+key 查表
// 移植自 C++ IpaDatabase.h/cpp

interface IpaKeyEntry { base: string; shift: boolean; chars: string[] }

// event.code → 逻辑键名 (与 JSON base 匹配)
const CODE_TO_LOGICAL: Record<string, string> = {
  KeyA: "A", KeyB: "B", KeyC: "C", KeyD: "D", KeyE: "E", KeyF: "F",
  KeyG: "G", KeyH: "H", KeyI: "I", KeyJ: "J", KeyK: "K", KeyL: "L",
  KeyM: "M", KeyN: "N", KeyO: "O", KeyP: "P", KeyQ: "Q", KeyR: "R",
  KeyS: "S", KeyT: "T", KeyU: "U", KeyV: "V", KeyW: "W", KeyX: "X",
  KeyY: "Y", KeyZ: "Z",
  Digit0: "0", Digit1: "1", Digit2: "2", Digit3: "3", Digit4: "4",
  Digit5: "5", Digit6: "6", Digit7: "7", Digit8: "8", Digit9: "9",
  Comma: ",", Period: ".", Semicolon: ";", Slash: "/",
  Backslash: "\\", Backquote: "`", Minus: "-", Quote: "'",
};

export function logicalNameFromCode(code: string): string | null {
  return CODE_TO_LOGICAL[code] ?? null;
}

// base 字符串 → 逻辑键名 (复刻 C++ qtKeyFromName)
const SYMBOL_MAP: Record<string, string> = {
  ",": ",", ".": ".", ";": ";", "/": "/",
  "\\": "\\", "`": "`", "~": "`", "-": "-", "_": "-",
  "'": "'", '"': "'",
};

function logicalNameFromBase(base: string): string | null {
  if (base.length === 0) return null;
  const ch = base[0];
  if (ch >= "A" && ch <= "Z") return ch;
  if (ch >= "a" && ch <= "z") return ch.toUpperCase();
  if (ch >= "0" && ch <= "9") return ch;
  // 跳过箭头键名 (Up/Down/Left/Right) — 它们会被映射到单字母 U/D/L/R 造成误匹配
  if (["Up", "Down", "Left", "Right"].includes(base)) return null;
  return SYMBOL_MAP[ch] ?? null;
}

class IpaDatabase {
  private keyMap = new Map<string, string[]>();
  private ready = false;

  async load(path = "/data/ipa_keymap.json"): Promise<void> {
    try {
      const resp = await fetch(assetUrl(path));
      const root = await resp.json();

      // 第一遍: 名称 → fromCodePoint 字符串 (支持多码点组合, 如 [593,771] = ɑ̃)
      const charToString = new Map<string, string>();
      const charsObj = root.chars as Record<string, number[]>;
      for (const [name, cps] of Object.entries(charsObj)) {
        charToString.set(name, String.fromCodePoint(...cps));
      }

      // 第二遍: keys → 候选字符串列表
      const keysArr = root.keys as IpaKeyEntry[];
      for (const entry of keysArr) {
        const logical = logicalNameFromBase(entry.base);
        if (!logical) continue;

        const strings: string[] = [];
        for (const name of entry.chars) {
          const s = charToString.get(name);
          if (s) strings.push(s);
        }
        if (strings.length === 0) continue;

        const key = `${logical}|${entry.shift ? "1" : "0"}`;
        // first-wins: 同键同shift只保留第一个 (与C++一致)
        if (!this.keyMap.has(key)) {
          this.keyMap.set(key, strings);
        }
      }

      this.ready = true;
      console.log("[IpaDb] loaded", charToString.size, "chars,", this.keyMap.size, "shortcuts");
    } catch (e) {
      console.error("[IpaDb] load error:", e);
    }
  }

  isReady(): boolean { return this.ready; }

  candidates(logical: string, shift: boolean): string[] {
    return this.keyMap.get(`${logical}|${shift ? "1" : "0"}`) ?? [];
  }
}

export const ipaDatabase = new IpaDatabase();
