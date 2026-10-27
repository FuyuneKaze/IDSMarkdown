import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl

mpl.rcParams['font.sans-serif'] = ['SimHei'] # 黑体

df = pd.read_csv(r"D:\2026harucpp\scripts\output\composition_v3.csv")

data = df[(df["op"] == "⿰") & (df["c2_char"] == "木")].dropna()

w_stre1 = data["c1_str_w"]
w_stre2 = data["c2_str_w"]

strok_1 = data["c1_strokes"]
strok_2 = data["c2_strokes"]

l_w_1 = list(w_stre1)
num_w1 = {i:l_w_1.count(i) for i in w_stre1}

#point = (strok_1/strok_2, w_stre1/w_stre2)
#plt.set_cmap()
'''point = list(num_w1.items())
plt.scatter([p[0] for p in point],[p[1] for p in point],s=5,alpha=0.6,c="#000000")'''
plt.hist(w_stre1,bins=20, density=True)
mu, sigma = np.mean(w_stre1), np.std(w_stre1)
x = np.linspace(min(w_stre1),max(w_stre1),100)
plt.plot(x,(1/(sigma * np.sqrt(2*np.pi))) * np.exp(-(x-mu)**2 / (2*sigma**2)),color = 'red')
#print(len(point))
plt.tight_layout()
print("mu=",mu,",sigma=",sigma)
plt.show()
#print(point)

