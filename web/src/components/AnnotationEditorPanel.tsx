import { useEffect, useState } from "react";
import type { AnnotationTarget } from "./Editor";

interface Props {
  target: AnnotationTarget | null;
  onInsert: (text: string) => void;
  onUpdate: (pos: number, text: string) => void;
}

/**
 * 双行小字注释编辑面板: 光标旁有块 → 实时回写; 无 → 草稿 + 插入
 */
export default function AnnotationEditorPanel({ target, onInsert, onUpdate }: Props) {
  const [text, setText] = useState("");

  useEffect(() => {
    setText(target?.text ?? "");
  }, [target]);

  const onChange = (v: string) => {
    setText(v);
    if (target) onUpdate(target.pos, v);
  };

  return (
    <>
      {target ? (
        <p className="form-hint">
          正在编辑光标旁的双行小字。文字按一半分割：横排先上后下，竖排先右后左（古籍）。
        </p>
      ) : (
        <p className="form-hint">
          将光标移到需要注释的位置（块会插入到光标处），或右键选择"双行小字注释"后在此输入。
        </p>
      )}
      <label className="form-label">注释文字</label>
      <input
        className="form-input"
        value={text}
        placeholder="請輸入註釋"
        //這deepseek還挺有意思自己寫了個“唐音不响，春天已深”當示例文字。
        onChange={(e) => onChange(e.target.value)}
        autoFocus
      />
      {!target && (
        <button className="form-btn primary" onClick={() => onInsert(text)}>
          插入到光标处
        </button>
      )}
    </>
  );
}
