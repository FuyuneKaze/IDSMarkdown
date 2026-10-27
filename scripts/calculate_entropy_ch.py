from PIL import Image, ImageDraw, ImageFont
import numpy as np
import math

def char_entropy(char, font_path=None, font_size=100):
    """
    计算单个字符的横向和纵向信息熵
    
    Args:
        char: 要计算的字符
        font_path: 字体文件路径（可选，不指定则使用默认字体）
        font_size: 字体大小
    
    Returns:
        dict: {'H_hor': 横向熵, 'H_ver': 纵向熵}
    """
    # 创建空白位图
    img = Image.new('L', (font_size, font_size), 'white')
    draw = ImageDraw.Draw(img)
    
    # 加载字体
    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size-20)
        else:
            # 使用默认字体
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # 在图片上绘制字符（黑色）
    draw.text((10, 10), char, fill='black', font=font)
    
    # 转为二值数组（黑色像素为1，白色为0）
    img_array = np.array(img)
    binary = (img_array < 128).astype(int)
    
    height, width = binary.shape
    total_pixels = height * width
    
    # 计算每行黑色像素数（横向分布）
    row_sums = np.sum(binary, axis=1)
    p_y = row_sums / total_pixels
    
    # 计算每列黑色像素数（纵向分布）
    col_sums = np.sum(binary, axis=0)
    p_x = col_sums / total_pixels
    
    # 计算熵
    def calc_entropy(prob_dist):
        prob_dist = prob_dist[prob_dist > 0]  # 去掉零概率
        return -np.sum(prob_dist * np.log(prob_dist))
    
    return {
        'H_hor': calc_entropy(p_y),
        'H_ver': calc_entropy(p_x),
        'row_dist': row_sums,
        'col_dist': col_sums
    }

# 使用示例
if __name__ == "__main__":
    # 计算单个字符
    char = '中'
    result = char_entropy(char)
    print(f"字符 '{char}':")
    print(f"  横向熵 H_hor = {result['H_hor']:.4f}")
    print(f"  纵向熵 H_ver = {result['H_ver']:.4f}")
    print()
    
    # 比较不同字符
    chars = ['口', '日', '目', '田', '罒', '鼻','一','二','三','丨','刀','川','丰','丨','艹','A','V','W','F','E','I']
    for c in chars:
        r = char_entropy(c,font_path=r'C:/Windows/Fonts/simhei.ttf')
        print(f"'{c}': H_hor={r['H_hor']:.4f}, H_ver={r['H_ver']:.4f}, kH={r['H_hor']/r['H_ver']}")