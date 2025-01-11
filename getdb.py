from openpyxl import Workbook
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
mplstyle.use('fast')
def GetData(file_path):
    count=0
    global x
    x=[]
    global y
    y=[]
    global z
    z=[]
    wb=Workbook()
    ws=wb.active
    #ws.append(title)
    print("维度\t\t\t\t精度\t\t\t\t全零\t\t海拔\t\t日数\t\t\t\t\t\t日期\t\t\t\t时间")
    #file_path='database/000/Trajectory/20081023025304.plt'
    with open(file_path,'r') as file:
        file_content=file.readlines()
    for line in file_content:

        if(count>5):
            x.append(float(line.strip().split(',')[0]))
            y.append(float(line.strip().split(',')[1]))
            z.append(float(line.strip().split(',')[3]))
            for i in range(len(line.strip().split(','))):
                ws.append(line.strip().split(','))#line.strip().split(',')
                print(line.strip().split(',')[i],end='\t\t')
                if i+1 not in range(len(line.strip().split(','))):
                    print("")
        count=count+1
    wb.save('data.xlsx')

    def draw(dim,lon,ati):
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1, projection="3d")
        #设置坐标轴范围
        plt.xlim(min(dim), max(dim))
        plt.ylim(min(lon), max(lon))

        # 逐步绘图
        plt.ion()
        ax.axis('off')
        #ax.scatter3D(xd, yd, zd, cmap='Blues')  # 绘制散点图
        for i in range(len(dim)):
            ax.plot(dim[:i],lon[:i],ati[:i], 'gray',clip_on=False)  # 绘制空间曲线
            if i%24==0:#定期暂停
                plt.pause(0.1)
        plt.ioff()
        plt.show()
    draw(x, y, z)


if __name__ == "__main__":
    GetData('database/000/Trajectory/20081023025304.plt')

    # print(x)
    # print(y)
    # print(z)