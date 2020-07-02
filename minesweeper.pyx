#cython: language_level=3
import random
from time import time
from PIL import Image, ImageDraw, ImageColor, ImageFont

cdef str COLUMN_NAME = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
cdef CELL_COVER = Image.new("RGB", (79, 79))
draw = ImageDraw.Draw(CELL_COVER)
draw.polygon([(0, 0), (0, 79), (79, 0)], fill=(255, 255, 255))
draw.polygon([(79, 79), (0, 79), (79, 0)], fill=(128, 128, 128))
draw.rectangle((10, 10, 79 - 10, 79 - 10), fill=(192, 192, 192))

cpdef enum GameState:
    PREPARE = 1
    GAMING = 2
    WIN = 3
    FAIL = 4

cdef class Cell:
    cdef public int row, column
    cdef public bint is_mine, is_mined, is_marked, is_checked
    def __init__(self, is_mine: bool, row: int = 0, column: int = 0, is_mined: bool = False, is_marked: bool = False):
        self.is_mine = is_mine
        self.is_mined = is_mined
        self.is_marked = is_marked
        self.row = row
        self.column = column
        self.is_checked = False

    def __str__(self):
        return f"[Cell] is_mine:{self.is_mine} is_marked:{self.is_marked} is_mined:{self.is_mined}"

cdef class MineSweeper:
    # 需要外部访问需要使用public
    cdef public int row, column, mines, actions
    cdef readonly float start_time
    cdef list panel
    cdef font
    cdef readonly GameState state
    def __init__(self, row: int, column: int, mines: int):
        if row > 26 or column > 26:
            raise ValueError("暂不支持这么大的游戏盘")
        if row < 5 or column < 5:
            raise ValueError("别闹，这么小怎么玩？")
        if mines >= row * column or mines == 0:
            raise ValueError("非法操作")
        # if mines < column - 1 or mines < row - 1:
        #     raise ValueError("就不能来点难的吗")
        if mines > row * column / 2:
            raise ValueError("这么多雷，你认真的吗？")
        self.row = row
        self.column = column
        self.mines = mines
        self.start_time = time()
        self.actions = 0
        self.font = ImageFont.truetype("00TT.TTF", 40)
        self.panel = [[Cell(False, row=r, column=c) for c in range(column)] for r in range(row)]
        self.state = GameState.PREPARE

    def __str__(self):
        return f"[MineSweeper] {self.mines} in {self.row}*{self.column}"

    def draw_panel(self) -> Image.Image:
        start = time() * 1000
        img = Image.new("RGB", (80 * self.column, 80 * self.row), (193, 193, 193))
        self.__draw_split_line(img)
        self.__draw_cell_cover(img)
        self.__draw_cell(img)
        print(f"draw spend {time() - start}ms at {str(self)}")
        return img
    # cdef 只能cython调用
    cdef __draw_split_line(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        cdef int i
        for i in range(0, self.row):
            draw.line((0, i * 80, img.size[0], i * 80), fill=(134,134,134))
        for i in range(0, self.column):
            draw.line((i * 80, 0, i * 80, img.size[1]), fill=(134,134,134))

    cdef __draw_cell_cover(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        cdef int i, j
        for i in range(0, self.row):
            for j in range(0, self.column):
                cell = self.panel[i][j]
                if self.state == GameState.FAIL and cell.is_mine:
                    draw.rectangle((j * 80 + 1, i * 80 + 1, (j + 1) * 80 - 1, (i + 1) * 80 - 1),
                                   fill=ImageColor.getrgb("red"))
                    continue
                if cell.is_marked:
                    draw.rectangle((j * 80 + 1, i * 80 + 1, (j + 1) * 80 - 1, (i + 1) * 80 - 1),
                                   fill=ImageColor.getrgb("blue"))
                    continue
                if not cell.is_mined:
                    # draw.rectangle((j * 80 + 1, i * 80 + 1, (j + 1) * 80 - 1, (i + 1) * 80 - 1),
                    #                fill=ImageColor.getrgb("gray"))
                    img.paste(CELL_COVER, (j * 80 + 1, i * 80 + 1))

    cdef __draw_cell(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        cdef int i, j
        index_font_size = self.font.getsize("AA")
        count_font_size = self.font.getsize("1")
        for i in range(0, self.row):
            for j in range(0, self.column):
                cell = self.panel[i][j]
                if not cell.is_mined:
                    index = f"{COLUMN_NAME[i]}{COLUMN_NAME[j]}"
                    center = (
                        80 * (j + 1) - (index_font_size[0] / 2) - 37, 80 * (i + 1) - 40 - (index_font_size[1] / 2))
                    draw.text(center, index, fill=ImageColor.getrgb("black"), font=self.font)
                else:
                    count = self.count_around(i, j)
                    if count == 0:
                        continue
                    center = (
                        80 * (j + 1) - (count_font_size[0] / 2) - 40, 80 * (i + 1) - 40 - (count_font_size[1] / 2))
                    draw.text(center, str(count), fill=self.__get_count_text_color(count), font=self.font)

    cdef __get_count_text_color(self, int count):
        if count == 1:
            return ImageColor.getrgb("green")
        if count == 2:
            return ImageColor.getrgb("orange")
        if count == 3:
            return ImageColor.getrgb("red")
        if count == 4:
            return ImageColor.getrgb("darkred")
        return ImageColor.getrgb("black")

    # 允许python调用
    cpdef void mine(self, int row, int column):
        if not self.__is_valid_location(row, column):
            raise ValueError("非法操作")
        cdef start = time() * 1000
        cdef Cell cell = self.panel[row][column]
        if cell.is_mined:
            raise ValueError("你已经挖过这里了")
        cell.is_mined = True
        if self.state == GameState.PREPARE:
            self.__gen_mine()
        if self.state != GameState.GAMING:
            raise ValueError("游戏已结束")
        self.actions += 1
        if cell.is_mine:
            self.state = GameState.FAIL
            return
        self.__reset_check()
        self.__spread_not_mine(row, column)
        self.__win_check()
        print(f"mine spend {time() - start}ms at {str(self)}")

    cpdef void tag(self, int row, int column):
        cdef Cell cell = self.panel[row][column]
        cdef start = time() * 1000
        if cell.is_mined:
            raise ValueError("你不能标记一个你挖开的地方")
        if self.state != GameState.GAMING and self.state != GameState.PREPARE:
            raise ValueError("游戏已结束")
        self.actions += 1
        if cell.is_marked:
            cell.is_marked = False
        else:
            cell.is_marked = True
        print(f"tag spend {time() - start}ms at {str(self)}")

    cdef void __gen_mine(self):
        cdef list mine_location = [random.randint(0, self.row * self.column) for i in range(self.mines)]
        cdef int row, column, location
        for location in mine_location:
            row = int(location / self.column)
            column = (location % self.column) - 1
            if column == -1:
                column = self.column - 1
                row -= 1
            if self.panel[row][column].is_mine or self.panel[row][column].is_mined:
                mine_location.append(random.randint(0, self.row * self.column))
                continue
            self.panel[row][column].is_mine = True
        self.state = GameState.GAMING

    cdef void __spread_not_mine(self, int row, int column):
        if not self.__is_valid_location(row, column):
            return
        cell = self.panel[row][column]
        if cell.is_checked:
            return
        if cell.is_mine:
            return
        cell.is_mined = True
        cell.is_checked = True
        cdef int count = self.count_around(row, column)
        if count > 0:
            return
        self.__spread_not_mine(row + 1, column)
        self.__spread_not_mine(row - 1, column)
        self.__spread_not_mine(row, column + 1)
        self.__spread_not_mine(row, column - 1)
        if count == 0:
            self.__spread_not_mine(row + 1, column + 1)
            self.__spread_not_mine(row - 1, column - 1)
            self.__spread_not_mine(row + 1, column - 1)
            self.__spread_not_mine(row - 1, column + 1)

    cdef void __reset_check(self):
        for i in range(0, self.row):
            for j in range(0, self.column):
                self.panel[i][j].is_checked = False

    cdef void __win_check(self):
        for i in range(0, self.row):
            for j in range(0, self.column):
                if (not self.panel[i][j].is_mined) and (not self.panel[i][j].is_mine):
                    return
        self.state = GameState.WIN

    cdef int count_around(self, int row, int column):
        cdef count = 0
        for r in range(row - 1, row + 2):
            for c in range(column - 1, column + 2):
                if not self.__is_valid_location(r, c):
                    continue
                if self.panel[r][c].is_mine:
                    count += 1
        if self.panel[row][column].is_mine:
            count -= 1
        return count

    @staticmethod
    def parse_input(input_text: str):
        if len(input_text) != 2:
            raise ValueError("非法位置")
        return COLUMN_NAME.index(input_text[0].upper()), COLUMN_NAME.index(input_text[1].upper())

    cdef bint __is_valid_location(self, int row, int  column):
        if row > self.row - 1 or column > self.column - 1 or row < 0 or column < 0:
            return False
        return True
