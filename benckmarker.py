import pyximport

pyximport.install()
import time
from minesweeper import MineSweeper

if __name__ == '__main__':
    start = time.time()
    for i in range(0, 100):
        mine = MineSweeper(25, 25, 25)
        mine.mine(5,5)
        mine.draw_panel()
    print(time.time() - start)
