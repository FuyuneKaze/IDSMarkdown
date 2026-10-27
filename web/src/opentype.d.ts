/**
 * opentype.js 最小类型声明 (项目未安装 @types/opentype.js)
 * 仅声明实际使用的 API, 其余按 any 处理
 */
declare module "opentype.js" {
  namespace opentype {
    type Path = any;
    type Glyph = any;
    type Font = any;
    const Path: new () => any;
    const Glyph: new (options?: any) => any;
    const Font: new (options?: any) => any;
  }
  const opentype: typeof opentype;
  export default opentype;
}
