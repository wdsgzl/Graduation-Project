
def GetData(file_path):
    count=0
    print("维度\t\t\t\t精度\t\t\t\t全零\t\t海拔\t\t日数\t\t\t\t\t\t日期\t\t\t\t时间")
    #file_path='database/000/Trajectory/20081023025304.plt'
    with open(file_path,'r') as file :
        file_content=file.readlines()
    for line in file_content:
        if(count>5):
            for i in range(len(line.strip().split(','))):
                #line.strip().split(',')
                print(line.strip().split(',')[i],end='\t\t')
                if i+1 not in range(len(line.strip().split(','))):
                    print("")
        count=count+1

if __name__ == "__main__":
    GetData('database/000/Trajectory/20081023025304.plt')