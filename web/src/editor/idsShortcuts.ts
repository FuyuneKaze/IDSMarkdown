/**
 * IDS 算符的快捷键字典 —— **唯一真理**
 *
 * 桌面端（idsNumpad 扩展）、手机工具条（Toolbar 的宫格）、以及 Ruby/夹注面板里
 * 的普通输入框，都应从这里取映射，避免三处各写一份。
 *
 * 方向码: U/D/L/R = 上/下/左/右, O = open(开口方向), C = closed(全包围),
 *         XX = 重叠, MI = 镜像, RO = 旋转, SU = 减去, UU/LL = 上下三叠 / 左右三并
 */
export const IDS_ALT_NUMPAD: Record<string, string> = {
  NumpadAdd: "⿱",      // UD
  NumpadSubtract: "⿰", // LR
  Numpad1: "⿺",        // RU
  Numpad2: "⿶",        // OU
  Numpad3: "⿽",        // LU
  Numpad4: "⿷",        // OR
  Numpad5: "⿴",        // OC
  Numpad6: "⿼",        // OL
  Numpad7: "⿸",        // RD
  Numpad8: "⿵",        // OD
  Numpad9: "⿹",        // LD
  Numpad0: "⿻",        // XX
  KeyM: "⿾",           // MI
  KeyT: "⿿",           // RO
  KeyJ: "㇯",           // SU
};

/** 三聚（Alt+Ctrl）: ⿳ 上中下 / ⿲ 左中右 */
export const TRITY_IDS_OPERATOR: Record<string, string> = {
  Equal: "⿳",           // UU
  Minus: "⿲",           // LL
  NumpadAdd: "⿳",       // UU
  NumpadSubtract: "⿲",  // LL
};

/**
 * 把一次按键翻译成 IDS 算符；不是算符键则返回 null。
 * Alt → 二元；Alt+Ctrl → 三聚。
 */
export function idsOpFromKey(e: {
  altKey: boolean; ctrlKey: boolean; metaKey: boolean; code: string;
}): string | null {
  if (!e.altKey || e.metaKey) return null;
  if (e.ctrlKey) return TRITY_IDS_OPERATOR[e.code] ?? null;
  return IDS_ALT_NUMPAD[e.code] ?? null;
}
