import { useEffect, useState } from "react";
import { panelKeyInsert, insertIntoField } from "../editor/panelKeys";
import type { RubyTarget } from "./Editor";

interface Props {
  target: RubyTarget | null;
  onInsert: (base: string, rt: string) => void;
  onUpdate: (pos: number, base: string, rt: string) => void;
}

/**
 * Ruby 注音编辑面板: 光标旁有 ruby 块 → 实时回写; 无 → 草稿 + 插入
 */
export default function RubyEditorPanel({ target, onInsert, onUpdate }: Props) {
  const [base, setBase] = useState("");
  const [rt, setRt] = useState("");

  // 目标变化 (含切换节点/撤销重做) 时同步表单
  useEffect(() => {
    setBase(target?.base ?? "");
    setRt(target?.rt ?? "");
  }, [target]);

  const onBaseChange = (v: string) => {
    if (target) {
      setBase(v);
      onUpdate(target.pos, v, rt);
    } else {
      setBase(v);
    }
  };
  const onRtChange = (v: string) => {
    if (target) {
      setRt(v);
      onUpdate(target.pos, base, v);
    } else {
      setRt(v);
    }
  };


  // 面板输入框继承主编辑器的快捷键 (Alt+算符 / Alt+字母→IPA)
  const onFieldKey = (e: React.KeyboardEvent<HTMLInputElement>, apply: (v: string) => void) => {
    const ins = panelKeyInsert(e as unknown as KeyboardEvent);
    if (ins) { e.preventDefault(); insertIntoField(e.currentTarget, ins, apply); }
  };

  return (
    <>
      {target ? (
        <p className="form-hint">正在编辑光标旁的字块，输入实时更新。</p>
      ) : (
        <p className="form-hint">将光标移到需要加注音的位置（块会插入到光标处），输入文字与注音后点击插入。</p>
      )}
      <label className="form-label">文字</label>
      <input
        className="form-input"
        value={base}
        placeholder="請輸入文字"
        onChange={(e) => onBaseChange(e.target.value)}
        onKeyDown={(e) => onFieldKey(e, onBaseChange)}
        autoFocus
      />
      <label className="form-label">注音</label>
      <input
        className="form-input"
        value={rt}
        placeholder="請輸入Ruby"
        onChange={(e) => onRtChange(e.target.value)}
        onKeyDown={(e) => onFieldKey(e, onRtChange)}
      />
      {!target && (
        <button className="form-btn primary" onClick={() => onInsert(base, rt)}>
          插入到光标处
        </button>
      )}
    </>
  );
}
