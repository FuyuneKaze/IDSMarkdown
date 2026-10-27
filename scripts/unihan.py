import json
class Unihan():
    def __init__(self,uni=""):
        self.uni=uni
        self.cjk=chr(int(self.uni[2:],16))
        self.cant=[]
        self.defi=""
        self.fanq=[]
        self.hangul=[]
        self.hypl=[]
        self.hypy=[]
        self.jap=[]
        self.japkun=[]
        self.japon=[]
        self.kor=[]
        self.mand=[]
        self.smszd=""
        self.tang=[]
        self.tghz=[]
        self.viet=[]
        self.xhc=[]
        self.zhuang=[]
    def set_info(self, entry):
        if isinstance(entry, str):
            entry = entry.split()
        name = entry[1]
        cont = entry[2:]
        match(name):
            case("kCantonese"):
                self.cant = cont
            case("kDefinition"):
                self.defi += ''.join([str(i) + " " for i in cont])
            case("kFanqie"):
                self.fanq = cont
            case("kHangul"):
                self.hangul = cont
            case("kHanyuPinlu"):
                self.hypl = cont
            case("kHanyuPinyin"):
                self.hypy = cont
            case("kJapanese"):
                self.jap = cont
            case("kJapaneseKun"):
                self.japkun = cont
            case("kJapaneseOn"):
                self.japon = cont
            case("kKorean"):
                self.kor = cont
            case("kMandarin"):
                self.mand = cont
            case("kSMSZD2003Readings"):
                self.smszd = ''.join([str(i) + " " for i in cont])
            case("kTang"):
                self.tang = cont
            case("kTGHZ2013"):
                self.tghz = cont
            case("kVietnamese"):
                self.viet = cont
            case("kXHC1983"):
                self.xhc = cont
            case("kZhuang"):
                self.zhuang = cont
            case _:
                pass
    def __str__(self):
        data = {
            "uni": self.uni,
            "cjk": self.cjk,
            "cant": self.cant,
            "defi": self.defi,
            "fanq": self.fanq,
            "hangul": self.hangul,
            "hypl": self.hypl,
            "hypy": self.hypy,
            "jap": self.jap,
            "japkun": self.japkun,
            "japon": self.japon,
            "kor": self.kor,
            "mand": self.mand,
            "smszd": self.smszd,
            "tang": self.tang,
            "tghz": self.tghz,
            "viet": self.viet,
            "xhc": self.xhc,
            "zhuang": self.zhuang
        }
        # 返回格式化的 JSON，ensure_ascii=False 保证中文正常显示
        return json.dumps(data, ensure_ascii=False, indent=2)

syllables = {
    # 清音
    "ア": "a", "イ": "i", "ウ": "u", "エ": "e", "オ": "o",
    "カ": "ka", "キ": "ki", "ク": "ku", "ケ": "ke", "コ": "ko",
    "サ": "sa", "シ": "si", "ス": "su", "セ": "se", "ソ": "so",
    "タ": "ta", "チ": "ti", "ツ": "tu", "テ": "te", "ト": "to",
    "ナ": "na", "ニ": "ni", "ヌ": "nu", "ネ": "ne", "ノ": "no",
    "ハ": "ha", "ヒ": "hi", "フ": "hu", "ヘ": "he", "ホ": "ho",
    "マ": "ma", "ミ": "mi", "ム": "mu", "メ": "me", "モ": "mo",
    "ヤ": "ya", "ユ": "yu", "ヨ": "yo",
    "ラ": "ra", "リ": "ri", "ル": "ru", "レ": "re", "ロ": "ro",
    "ワ": "wa", "ヲ": "wo", "ヰ": "wi", "ヱ": "we", "ン": "n",
    "ガ": "ga", "ギ": "gi", "グ": "gu", "ゲ": "ge", "ゴ": "go",
    "ザ": "za", "ジ": "zi", "ズ": "zu", "ゼ": "ze", "ゾ": "zo",
    "ダ": "da", "ヂ": "di", "ヅ": "du", "デ": "de", "ド": "do",
    "バ": "ba", "ビ": "bi", "ブ": "bu", "ベ": "be", "ボ": "bo",
    "パ": "pa", "ピ": "pi", "プ": "pu", "ペ": "pe", "ポ": "po",
    "キャ": "kya", "キュ": "kyu", "キョ": "kyo",
    "シャ": "sya", "シュ": "syu", "ショ": "syo",
    "チャ": "tya", "チュ": "tyu", "チョ": "tyo",
    "ニャ": "nya", "ニュ": "nyu", "ニョ": "nyo",
    "ヒャ": "hya", "ヒュ": "hyu", "ヒョ": "hyo",
    "ミャ": "mya", "ミュ": "myu", "ミョ": "myo",
    "リャ": "rya", "リュ": "ryu", "リョ": "ryo",
    "ギャ": "gya", "ギュ": "gyu", "ギョ": "gyo",
    "ジャ": "zya", "ジュ": "zyu", "ジョ": "zyo",
    "ヂャ": "dya", "ヂュ": "dyu", "ヂョ": "dyo",
    "ビャ": "bya", "ビュ": "byu", "ビョ": "byo",
    "ピャ": "pya", "ピュ": "pyu", "ピョ": "pyo",
    "ファ": "fa", "フィ": "fi", "フェ": "fe", "フォ": "fo",
    "ウィ": "wi", "ウェ": "we", "ウォ": "wo",
    "ヴァ": "va", "ヴィ": "vi", "ヴ": "vu", "ヴェ": "ve", "ヴォ": "vo",
    "シェ": "sye", "ジェ": "zye", "チェ": "tye",
    "ティ": "ti", "トゥ": "tu",
    "ディ": "di", "ドゥ": "du", "デュ": "dyu",
    "テュ": "tyu",
    "ツァ": "tsa", "ツィ": "tsi", "ツェ": "tse", "ツォ": "tso",
    "イェ": "ye",
    "クァ": "kwa", "クィ": "kwi", "クェ": "kwe", "クォ": "kwo",
    "グァ": "gwa",
    "ッカ": "kka", "ッキ": "kki", "ック": "kku", "ッケ": "kke", "ッコ": "kko",
    "ッサ": "ssa", "ッシ": "ssi", "ッス": "ssu", "ッセ": "sse", "ッソ": "sso",
    "ッタ": "tta", "ッチ": "tti", "ッツ": "ttu", "ッテ": "tte", "ット": "tto",
    "ッパ": "ppa", "ッピ": "ppi", "ップ": "ppu", "ッペ": "ppe", "ッポ": "ppo",
    "ッチャ": "ttya", "ッチュ": "ttyu", "ッチョ": "ttyo",
    "ッシャ": "ssya", "ッシュ": "ssyu", "ッショ": "ssyo",
    "ッヒャ": "hhya", "ッヒュ": "hhyu", "ッヒョ": "hhyo",
}    
'''def ex_line(line):
    entrys = line.split()
    newunihan = Unihan(entrys[0])
'''
with open(r"D:\2026harucpp\data\dictionary\Unihan_Readings.txt",encoding="utf-8") as dic:
    ent = dic.readlines()
unihandict = {}

def kanatoromaji(string,syll):
    hira = False
    sylldic = sorted(syll.keys(), key=len, reverse=True)
    nstr = ""
    for i in range(len(string)):
        s=string[i]
        if ord(s)>=0x3041 and ord(s)<=0x3096:
            hira = True
            nstr+=chr(ord(s)+(0x30a1-0x3041))
        else:
            nstr+=s
    string=nstr
    i = 0
    result = []
    while i < len(string):
        matched = False
        
        # 从最长的键开始尝试匹配
        for key in sylldic:
            if string[i:i+len(key)] == key:
                result.append(syll[key])
                i += len(key)
                matched = True
                break
        
        if not matched:
            # 未匹配的字符保留原样
            result.append(string[i])
            i += 1

    return (hira,''.join(result))


for line in ent:
    if line[0] == "#" or line[0] != "U":
        continue
    entries = line.split()
    unic = entries[0]
    if unic not in unihandict.keys():
        newUnihan = Unihan(unic)
        newUnihan.set_info(entries)
        unihandict[unic] = newUnihan
    else:
        Unih = unihandict[unic]
        Unih.set_info(entries)
        unihandict[unic] = Unih

'''with open(r"D:\\2026harucpp\\data\\dictionary\\Unihan.txt","w",encoding="utf-8") as fw:
    for u in unihandict:
        fw.write(unihandict[u].__str__())'''
with open(r"D:\\2026harucpp\\data\\dictionary\\jap_cjk.json","w",encoding="utf-8") as fw:
    japtocjk = {}
    for u in unihandict:
        uni = unihandict[u]
        for doku in uni.jap:
            hou,doku = kanatoromaji(doku,syllables)#hou=true:ondoku
            if doku in japtocjk.keys():
                if hou:
                    japtocjk[doku][1].append(uni.cjk)
                else:
                    japtocjk[doku][0].append(uni.cjk)
            else:
                japtocjk[doku] = [[],[]]
                if hou:
                    japtocjk[doku][1].append(uni.cjk)
                else:
                    japtocjk[doku][0].append(uni.cjk)
    fw.write("{\n")
    for doku in sorted(japtocjk.keys()):
        if japtocjk[doku] != []:
            wc = {"on": sorted(japtocjk[doku][0]),"kun":sorted(japtocjk[doku][1])}
            fw.write(f"\"{doku}\": ")
            fw.write(json.dumps(wc,ensure_ascii=False, indent = None))
            fw.write(",\n")
            #fw.write(f"{doku}: {''.join(sorted([str(i) + " " for i in japtocjk[doku]]))}\n")
    fw.write("\n}")
'''with open(r"D:\\2026harucpp\\data\\dictionary\\hangul_cjk.txt","w",encoding="utf-8") as fw:
    hantocjk = {}
    for u in unihandict:
        uni = unihandict[u]
        for dok in uni.hangul:
            dok = dok[0]
            if dok in hantocjk.keys():
                hantocjk[dok].append(uni.cjk)
            else:
                hantocjk[dok] = [uni.cjk]
    
    for dok in sorted(hantocjk.keys()):
        if hantocjk[dok] != []:
            fw.write(f"{dok}: {''.join(sorted([str(i) + " " for i in hantocjk[dok]]))}\n")'''
with open(r"D:\\2026harucpp\\data\\dictionary\\hangul_cjk.json","w",encoding="utf-8") as fw:
    hantocjk = {}
    for u in unihandict:
        uni = unihandict[u]
        han = uni.hangul
        if len(han) >= 1:
            han = han[0][0]
        for dok in uni.kor:
            dok = dok.lower()
            if dok in hantocjk.keys():
                hantocjk[dok][1].append(uni.cjk)
                if hantocjk[dok][0] == []:
                    hantocjk[dok][0] = han
            else:
                #hantocjk[dok] = [han]
                hantocjk[dok] = [han]
                hantocjk[dok].append([uni.cjk])
    fw.write("{\n")
    for dok in sorted(hantocjk.keys()):
        if hantocjk[dok] != []:
            wc = {"hangul":hantocjk[dok][0],"cjk":sorted(hantocjk[dok][1])}
            fw.write(f"\"{dok}\": ")
            fw.write(json.dumps(wc,ensure_ascii=False,indent=None))
            fw.write(",\n")
            #fw.write(f"{dok}: {''.join(sorted([str(i) + " " for i in hantocjk[dok]]))}\n")
    fw.write("\n}")
'''with open(r"D:\\2026harucpp\\data\\dictionary\\viet_cjk.txt","w",encoding="utf-8") as fw:
    viettocjk = {}
    for u in unihandict:
        uni = unihandict[u]
        for dok in uni.viet:
            if dok in viettocjk.keys():

                viettocjk[dok].append(uni.cjk)
            else:
                viettocjk[dok] = [uni.cjk]
    
    for dok in sorted(viettocjk.keys()):
        if viettocjk[dok] != []:
            fw.write(f"{dok}: {''.join(sorted([str(i) + " " for i in viettocjk[dok]]))}\n")'''
