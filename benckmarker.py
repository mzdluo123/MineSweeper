import pyximport

pyximport.install()
import time
from minesweeper import MineSweeper

if __name__ == '__main__':
    start = time.time()
    for i in range(0, 200):
        mine = MineSweeper(25, 25, 300)
        mine.mine(5, 5)
    print(time.time() - start)
