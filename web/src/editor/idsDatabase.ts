import { isIdsOperator } from "./charUtils";

/**
 * IDS 数据库 — 从 C++ IdsDatabase.cpp 移植
 *
 * 功能：
 * 1. normalize(ids) — 清理 IDS 表达式（去注释、括号、位置标记）
 * 2. lookup(ids)   — 反向查找标准化 IDS → Unicode 字符
 * 3. load(data)    — 加载 TSV 格式的 IDS 数据
 */
export class IdsDatabase {
  private reverseMap = new Map<string, string>();

  /**
   * 清理 IDS 序列为可匹配的标准形式
   * "⿱一.亅"     → "⿱一亅"
   * "⿻乚.一.(.);..."→ "⿻乚一"
   */
  normalize(rawIds: string): string {
    if (!rawIds) return "";
    if (rawIds.startsWith("#")) return "";

    // 取 ; 分隔的第一个片段
    let text = rawIds.split(";")[0];
    // 取 Tab 分隔的第一个变体
    text = text.split("\t")[0];

    // 去掉括号标记块: #(...), {...}, [...], (...)
    text = text.replace(/#\([^)]*\)|\{[^}]*\}|\[[^\]]*\]|\([^)]*\)/g, "");

    // 去掉 . 位置标记
    text = text.replace(/\./g, "");

    text = text.trim();
    if (!text) return "";

    // 必须以 IDS 操作符开头
    if (!isIdsOperator(text.charCodeAt(0))) return "";

    return text;
  }

  /**
   * 加载 TSV 数据: 字符\tIDS序列[\t变体2...]
   */
  load(data: string): void {
    const lines = data.split("\n");
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      const fields = trimmed.split("\t");
      if (fields.length < 2) continue;

      const targetChar = fields[0].trim();
      if (!targetChar) continue;

      for (let i = 1; i < fields.length; i++) {
        const ids = fields[i].trim();
        if (!ids) continue;

        const normalized = this.normalize(ids);
        if (!normalized) continue;

        // lv0 优先，后来的不覆盖
        if (!this.reverseMap.has(normalized)) {
          this.reverseMap.set(normalized, targetChar);
        }
      }
    }
  }

  /**
   * 根据清理后的 IDS 查找对应 Unicode 字符
   * 找到 → 返回字符，找不到 → 返回 undefined
   */
  lookup(normalizedIds: string): string | undefined {
    return this.reverseMap.get(normalizedIds);
  }

  /** 数据库中 IDS 条目总数 */
  get size(): number {
    return this.reverseMap.size;
  }
}
