import re

with open(r"D:\2026harucpp\data\dictionary\extend_hangul_name.txt",encoding="utf-8") as fr:
    lines = fr.readlines()
    dic_1={}
    dic_2={}
    dic_3={}
    dic_sta={}
    start=0x00
    end=0x00
    unipat = r"U\+(\w+)~"
    flag = ""
    for line in lines:
        line.strip()
        if not line:
            continue
        '''if start > end:
            continue'''
        if line.startswith("U+"):
            start = int("0x"+re.match(unipat,line).group(1),16)
            end = int("0x"+re.findall(r"~U\+(\w+)",line)[0],16)
            #print(start,end)
            flag = line
            continue
        #print(flag,chr(start),line)
        if "静态" in flag:
            if start>end:continue
            dic_sta[chr(start)] = line.strip()
        elif "初声" in flag:
            #print(1,chr(start),line)
            if start>end:continue
            dic_1[chr(start)] = line.strip()
        elif "中声" in flag:
            if start>end:continue
            #print(2,chr(start),line)
            dic_2[chr(start)] = line.strip()
        elif "终声" in flag:
            if start>end:continue
            #print(3,chr(start),line)
            dic_3[chr(start)] = line.strip()
        start += 1
    #print(dic)
    '''print("初声")
    for key in dic_1:
        print(f"{key}  :  {dic_1[key]}  ")
    print("中声")
    for key in dic_2:
        print(f"{key}  :  {dic_2[key]}  ")
    print("终声")
    for key in dic_3:
        print(f"{key}  :  {dic_3[key]}  ")'''
with open(r"D:\2026harucpp\data\dictionary\extend_hangul_map.json","w",encoding="utf-8") as fw:
    fw.write("\"choseong\": {\n")
    for key in dic_1:
        fw.write(f"\"{dic_1[key]}\" : \"{key}\", \n")
    fw.write("}\n\"junseong\": {\n")
    for key in dic_2:
        fw.write(f"\"{dic_2[key]}\" : \"{key}\", \n")
    fw.write("}\n\"junseong\": {\n")
    for key in dic_3:
        fw.write(f"\"{dic_3[key]}\" : \"{key}\", \n")
    fw.write("}")