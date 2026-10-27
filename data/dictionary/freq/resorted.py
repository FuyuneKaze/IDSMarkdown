def get_txt(path):
    if not path.startswith("D:"):
        path = r"D:\2026harucpp\data\dictionary\\"+path
    with open(path,encoding="utf-8") as f:
        txt=f.read()
    return txt
def var_dict(var_txt):
    """
    使用并查集构建异体字映射
    所有互为异体字的字都指向同一个主字（组内第一个字）
    """
    # 1. 解析所有异体字组
    groups = var_txt.strip('|').split('|')
    groups = [g for g in groups if g]  # 过滤空组
    
    # 2. 构建并查集
    parent = {}
    
    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            # 让较小的字作为根（字典序或码位）
            if px < py:
                parent[py] = px
            else:
                parent[px] = py
    
    # 3. 合并每个异体字组
    for group in groups:
        chars = list(group)
        if len(chars) > 1:
            first = chars[0]
            for ch in chars[1:]:
                union(first, ch)
    
    # 4. 构建映射表 {变体: 主字}
    variant_map = {}
    for ch in parent:
        root = find(ch)
        if ch != root:  # 只记录变体到主字的映射
            variant_map[ch] = root
    return variant_map

def var_dict1(var_txt):
    pass
def find_sort(list1,list2,list3=[],var={}):
    res = []
    def find_var(l,c,v):
        if c in v.keys():
            for cp in l:
                pass
    for ch in list2:
        if ch in list1:
            res.append(ch)
            list1.remove(ch)
    if list1 != [] and list3 != []:
        for ch in list3:
            if ch in list1:
                res.append(ch)
                list1.remove(ch)
    res+(list1)
    return res

from collections import defaultdict
def reorder(items, freq_list, variant_map):

    if not items:
        return []
    
    # 第一步：构建频率索引 {字: 位置}
    freq_index = {ch: idx for idx, ch in enumerate(freq_list)}
    
    # 第二步：分组 - 主字组和异体字组
    main_group = []           # 主字（包括实际作为主字的变体）
    variant_groups = defaultdict(list)  # 主字 -> [异体字列表]
    processed_as_variant = set()  # 记录哪些字被当作异体字处理了
    
    for ch in items:
        if ch in variant_map:
            main_ch = variant_map[ch]  # 找到主字
            
            # 检查主字是否在当前列表中
            if main_ch in items or main_ch in main_group:
                # 主字存在，作为异体字处理
                variant_groups[main_ch].append(ch)
                processed_as_variant.add(ch)
            else:
                
                # 主字不存在，把当前字当作主字
                # 检查是否已经被当作异体字处理了
                if ch not in processed_as_variant:
                    #print(ch)
                    main_group.append(ch)
        else:
            # 不是异体字，作为主字
            if ch not in processed_as_variant:
                main_group.append(ch)
    
    # 第三步：按频率排序主字（取组内最优频率，主字不存在于freq_list时排在最后）
    def best_rank(ch):
        best = freq_index.get(ch, float('inf'))
        for v in variant_groups.get(ch, []):
            v_rank = freq_index.get(v, float('inf'))
            if v_rank < best:
                best = v_rank
        return best
    main_group.sort(key=best_rank)
    
    # 第四步：构建结果 - 主字后面紧跟其异体字
    result = []
    for main_ch in main_group:
        result.append(main_ch)
        # 如果有异体字，按原顺序跟在后面
        if main_ch in variant_groups:
            # 对异体字也按频率排序（可选）
            #variant_groups[main_ch].sort(key=lambda x: freq_index.get(x, float('inf')))
            result.extend(variant_groups[main_ch])
    
    return result

def txt_order(path):
    freq_0 = get_txt(path)
    line_0 = freq_0.split("\n")
    fred = []
    for l in line_0:
        cjk = l.split("\t")[0]
        fred.append(cjk)
    return fred


import json

var_t = get_txt(r"freq//异体字.txt")
vard = var_dict(var_t)


json_j = get_txt(r"jap_cjk.json")
dict_j = json.loads(json_j)
json_k = get_txt(r"hangul_cjk.json")
dict_k = json.loads(json_k)
txt_viet = get_txt(r"viet_cjk.txt")

#fred_c = txt_order(r"freq//chn_freq.txt")
fred_j = txt_order(r"freq//jap_freq.txt")
fred_k = txt_order(r"freq//kor_freq.txt")
fred_v = txt_order(r"freq//viet_freq.txt")

# --- 日语 ---
for doku in dict_j:
    ondoku = dict_j[doku]["on"]
    kundoku = dict_j[doku]["kun"]

    dict_j[doku]["on"] = reorder(ondoku,fred_j,vard)
    dict_j[doku]["kun"] = reorder(kundoku,fred_j,vard)

with open(r"D:\2026harucpp\data\dictionary\\freq\\jap_cjk_s.txt","w",encoding="utf-8") as fw:
    json.dump(dict_j,fw,ensure_ascii=False,indent=None)

# --- 韩语 ---
for reading in dict_k:
    cjk_list = dict_k[reading]["cjk"]
    dict_k[reading]["cjk"] = reorder(cjk_list, fred_k, vard)

with open(r"D:\2026harucpp\data\dictionary\\freq\\hangul_cjk_s.txt","w",encoding="utf-8") as fw:
    json.dump(dict_k, fw, ensure_ascii=False, indent=None)

# --- 越南语 ---
dict_v = {}
for line in txt_viet.split("\n"):
    line = line.strip()
    if not line or ":" not in line:
        continue
    reading, chars_str = line.split(":", 1)
    chars = chars_str.strip().split()
    dict_v[reading] = reorder(chars, fred_v, vard)

with open(r"D:\2026harucpp\data\dictionary\\freq\\viet_cjk_s.txt","w",encoding="utf-8") as fw:
    out_lines = []
    for reading, chars in dict_v.items():
        out_lines.append(f"{reading}: {' '.join(chars)}")
    fw.write("\n".join(out_lines))

