import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl

mpl.rcParams['font.sans-serif'] = ['SimHei'] # 黑体
# ====== 用户配置区域（请在此修改参数）======
CSV_FILE = r"D:\2026harucpp\scripts\output\composition_ratios_v2.csv"           # CSV文件路径
FILTER_COL1 = "comp"             # 用于筛选的列名
FILTER_VAL1 = "山"                # 筛选条件（该列等于此值）
FILTER_COL2 = "pos"
FILTER_VAL2 = "left"
TARGET_COL = "bbox_w"             # 要提取数据的列名
# ==========================================

# 读取CSV
df = pd.read_csv(CSV_FILE)

# 筛选满足条件的行，并提取目标列数据
data = df[(df[FILTER_COL1] == FILTER_VAL1) & (df[FILTER_COL2] == FILTER_VAL2)][TARGET_COL].dropna()

# 绘制直方图与正态分布曲线
plt.hist(data, bins=20, density=True, alpha=0.7, color='skyblue', edgecolor='black')

# 拟合正态分布曲线
mu, sigma = np.mean(data), np.std(data)
x = np.linspace(min(data), max(data), 100)
plt.plot(x, (1/(sigma * np.sqrt(2*np.pi))) * np.exp(-(x-mu)**2 / (2*sigma**2)), 
         color='red', linewidth=2, label=f'正态分布 (μ={mu:.2f}, σ={sigma:.2f})')

plt.xlabel(TARGET_COL)
plt.ylabel('概率密度')
plt.title(f'{FILTER_COL1}={FILTER_VAL1},{FILTER_COL2}={FILTER_VAL2}')
plt.legend()
plt.grid(alpha=0.3)

plt.savefig(fr"D:\2026harucpp\scripts\output\static\{TARGET_COL}{FILTER_VAL1}{FILTER_VAL2}.png")
plt.show()