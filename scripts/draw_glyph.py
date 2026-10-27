import matplotlib.pyplot as plt
import numpy as np
from scipy.special import comb

def bernstein_poly(i, n, t):
    """贝塞尔基函数"""
    return comb(n, i) * (t ** i) * ((1 - t) ** (n - i))

def bezier_curve(points, num_points=50):
    """绘制贝塞尔曲线"""
    n = len(points) - 1
    t = np.linspace(0, 1, num_points)
    curve = np.zeros((num_points, 2))
    
    for i in range(n + 1):
        curve += np.outer(bernstein_poly(i, n, t), points[i])
    
    return curve



def parse_and_draw_bezier(data):
    """解析并绘制贝塞尔曲线"""
    fig, ax = plt.subplots(figsize=(10, 10))
    colors = ['blue', 'green', 'orange', 'purple', 'red']
    
    if isinstance(data,dict):
        enum = enumerate(data['contours'])
    elif isinstance(data,list):
        enum = enumerate(data)

    for idx, contour in enum:
        points = np.array(contour)
        x = points[:, 0]
        y = points[:, 1]
        y *= -1
        flags = points[:, 2]
        
        color = colors[idx % len(colors)]
        
        # 找到所有在曲线上的点（flag=0）
        on_curve_indices = [i for i, f in enumerate(flags) if f == 0]
        
        contour_segments = []

        # 如果有控制点，绘制贝塞尔曲线段
        if len(on_curve_indices) >= 2:
            # 处理每个曲线段
            for i in range(len(on_curve_indices)):
                start_idx = on_curve_indices[i]
                end_idx = on_curve_indices[(i + 1) % len(on_curve_indices)]
                
                # 获取该段的所有点（包括控制点）
                if start_idx < end_idx:
                    segment_points = points[start_idx:end_idx + 1]
                else:
                    # 处理循环到开头的情况
                    segment_points = np.vstack([points[start_idx:], points[:end_idx + 1]])
                
                # 过滤出该段的点（包括起点和终点）
                if len(segment_points) >= 2:
                    # 分离在曲线上的点和控制点
                    segment_on_curve = [p for p in segment_points if p[2] == 0]
                    segment_off_curve = [p for p in segment_points if p[2] == 1]
                    
                    # 构建贝塞尔曲线的控制点序列
                    bezier_points = []
                    
                    # 添加起点
                    bezier_points.append(segment_on_curve[0][:2])
                    
                    # 添加控制点
                    for p in segment_off_curve:
                        bezier_points.append(p[:2])
                    
                    # 添加终点
                    bezier_points.append(segment_on_curve[-1][:2])
                    
                    # 绘制贝塞尔曲线
                    if len(bezier_points) > 1:
                        curve_points = bezier_curve(np.array(bezier_points),100)
                        ax.plot(curve_points[:, 0], curve_points[:, 1], color=color, linewidth=0)
                        contour_segments.append(curve_points)
        
        if contour_segments:
            x = np.concatenate([seg[:, 0] for seg in contour_segments])
            y = np.concatenate([seg[:, 1] for seg in contour_segments])
            if len(x) > 1:
                x = np.append(x, x[0])
                y = np.append(y, y[0])
                ax.fill(x, y, color="#000000", alpha=0.9, zorder=0)
        
        # 绘制所有顶点
        '''for i, (xi, yi, flag) in enumerate(zip(x, y, flags)):
            if flag == 0:  # 在曲线上的点
                ax.scatter(xi, yi, color='red', s=50, zorder=5)
                ax.annotate(f'{i}', (xi, yi), fontsize=8, 
                           xytext=(5, 5), textcoords='offset points')
            else:  # 控制点
                ax.scatter(xi, yi, color='green', s=30, zorder=5, marker='s')
                ax.annotate(f'c{i}', (xi, yi), fontsize=8, 
                           xytext=(5, -10), textcoords='offset points')'''
        
        # 连接控制点（虚线）
        for i in range(len(points)):
            next_i = (i + 1) % len(points)
            if points[i][2] == 1 or points[next_i][2] == 1:
                ax.plot([points[i][0], points[next_i][0]], 
                       [points[i][1], points[next_i][1]], 
                       'gray', linestyle=':', alpha=0.5)
    
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    #ax.set_title(f"Bezier Curves: {data['name']}")
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_xlim(0,200)
    ax.set_ylim(-200,0)
    #ax.legend()
    
    plt.tight_layout()
    plt.show()

# 使用你的数据
data = {
    'name': 'u7389-j',
    'contours': 
        [[[36, 26, 0], [36, 181, 0], [24, 187, 0], [24, 20, 0]], [[30, 26, 0], [170, 26, 0], [170, 30, 0], [30, 30, 0]], [[176, 28, 0], [176, 178, 0], [164, 184, 0], [164, 28, 0]], [[164, 26, 0], [170, 21, 0], [181, 30, 0], [176, 34, 0], [164, 28, 0]], [[30, 170, 0], [170, 170, 0], [170, 174, 0], [30, 174, 0]], [[125.3, 114.7, 0], [130, 116.8, 0], [134.5, 119.1, 0], [138.8, 121.7, 0], [142.9, 124.6, 0], [146.7, 127.7, 0], [150.5, 131.1, 0], [154, 134.6, 0], [157.4, 138.3, 0], [160.5, 142.2, 0], [163.5, 146.3, 0], [153.3, 152.5, 0], [151.1, 148.5, 0], [148.8, 144.7, 0], [146.3, 140.9, 0], [143.6, 137.2, 0], [140.8, 133.6, 0], [137.8, 130.1, 0], [134.6, 126.7, 0], [131.3, 123.2, 0], [127.9, 119.7, 0], [124.3, 116.2, 0]], [[163.5, 146.3, 0], [164.2, 150.8, 0], [161.5, 154.5, 0], [157, 155.2, 0], [153.3, 152.5, 0]]]
        
}
'''[[125.3, 114.7, 0], [130, 116.8, 0], [134.5, 119.1, 0], [138.8, 121.7, 0], 
         [142.9, 124.6, 0], [146.7, 127.7, 0], [150.5, 131.1, 0], [154, 134.6, 0], 
         [157.4, 138.3, 0], [160.5, 142.2, 0], [163.5, 146.3, 0], [153.3, 152.5, 0], 
         [151.1, 148.5, 0], [148.8, 144.7, 0], [146.3, 140.9, 0], [143.6, 137.2, 0], 
         [140.8, 133.6, 0], [137.8, 130.1, 0], [134.6, 126.7, 0], [131.3, 123.2, 0], 
         [127.9, 119.7, 0], [124.3, 116.2, 0]],
        [[163.5, 146.3, 0], [164.2, 150.8, 0], [161.5, 154.5, 0], [157, 155.2, 0], 
         [153.3, 152.5, 0]]]'''
#parse_and_draw_bezier(data)


def create_bezier_svg(data, filename='bezier.svg'):
    """生成包含贝塞尔曲线的SVG"""
    
    # 计算边界
    all_points = []
    for contour in data['contours']:
        all_points.extend([(p[0], p[1]) for p in contour])
    
    min_x = min(p[0] for p in all_points) - 20
    min_y = min(p[1] for p in all_points) - 20
    max_x = max(p[0] for p in all_points) + 20
    max_y = max(p[1] for p in all_points) + 20
    
    width = max_x - min_x
    height = max_y - min_y
    
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{min_x} {min_y} {width} {height}">
    <rect width="100%" height="100%" fill="#f8f9fa"/>
    <g>
'''
    
    for contour in data['contours']:
        # 构建SVG路径
        path_parts = []
        i = 0
        
        while i < len(contour):
            if contour[i][2] == 0:  # 在曲线上的点
                if i == 0:
                    path_parts.append(f'M {contour[i][0]} {contour[i][1]}')
                else:
                    # 检查是否有控制点
                    if i + 1 < len(contour) and contour[i+1][2] == 1:
                        # 有控制点，构建贝塞尔曲线
                        start = contour[i]
                        controls = []
                        j = i + 1
                        while j < len(contour) and contour[j][2] == 1:
                            controls.append(contour[j])
                            j += 1
                        if j < len(contour) and contour[j][2] == 0:
                            end = contour[j]
                            if len(controls) == 1:
                                # 二次贝塞尔
                                path_parts.append(f'Q {controls[0][0]} {controls[0][1]}, {end[0]} {end[1]}')
                            elif len(controls) == 2:
                                # 三次贝塞尔
                                path_parts.append(f'C {controls[0][0]} {controls[0][1]}, {controls[1][0]} {controls[1][1]}, {end[0]} {end[1]}')
                            i = j
                        else:
                            # 没有结束点，直接连线
                            path_parts.append(f'L {contour[i][0]} {contour[i][1]}')
                    else:
                        path_parts.append(f'L {contour[i][0]} {contour[i][1]}')
            i += 1
        
        # 闭合路径
        if path_parts:
            path_parts.append('Z')
            path_str = ' '.join(path_parts)
            svg_content += f'        <path d="{path_str}" fill="rgba(0,123,255,0.1)" stroke="#007bff" stroke-width="2"/>\n'
    
    svg_content += '''    </g>
</svg>'''
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"SVG saved to {filename}")

#create_bezier_svg(data, r'D:\2026harucpp\scripts\bezier_contour.svg')