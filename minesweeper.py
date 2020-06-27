from PIL import Image, ImageDraw, ImageColor, ImageFont
from enum import Enum
import random

COLUMN_NAME = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class GameState(Enum):
    PREPARE = 1
    GAMING = 2
    WIN = 3
    FAIL = 4


class Cell:
    def __init__(self, is_mine: bool, row: int = 0, column: int = 0, is_mined: bool = False, is_marked: bool = False):
        self.is_mine = is_mine
        self.is_mined = is_mined
        self.is_marked = is_marked
        self.row = row
        self.column = column


def __str__(self):
    return f"[Cell] {self.is_mine}"


class MineSweeper:
    def __init__(self, row: int, column: int, mines: int):
        self.row = row
        self.column = column
        self.mines = mines
        self.font = ImageFont.truetype("00TT.TTF", 40)
        self.panel = [[Cell(False, row=r, column=c) for c in range(column)] for r in range(row)]
        self.state = GameState.PREPARE

    def draw_panel(self) -> Image.Image:
        img = Image.new("RGB", (80 * self.column, 80 * self.row), (255, 255, 255))
        self.__draw_split_line(img)
        self.__draw_cell_cover(img)
        self.__draw_cell(img)
        return img

    def __draw_split_line(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        for i in range(0, self.row):
            draw.line((0, i * 80, img.size[0], i * 80), fill=ImageColor.getrgb("black"))
        for i in range(0, self.column):
            draw.line((i * 80, 0, i * 80, img.size[1]), fill=ImageColor.getrgb("black"))

    def __draw_cell_cover(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        for i in range(0, self.row):
            for j in range(0, self.column):
                cell = self.panel[i][j]
                if cell.is_marked:
                    draw.rectangle((i + 1, j + 1, (i + 1) * 80 - 1, (j + 1) * 80 - 1), fill=ImageColor.getrgb("blue"))
                if not cell.is_mined:
                    draw.rectangle((i + 1, j + 1, (i + 1) * 80 - 1, (j + 1) * 80 - 1), fill=ImageColor.getrgb("gray"))

    def __draw_cell(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        for i in range(0, self.row):
            for j in range(0, self.column):
                cell = self.panel[i][j]
                if cell.is_mined:
                    font_size = self.font.getsize("1A")
                    index = f"{i}{COLUMN_NAME[j]}"
                    center = (80 * (i + 1) - (font_size[0] / 2) - 40, 80 * (j + 1) - 40 - (font_size[1] / 2))
                    draw.text(center, index, fill=ImageColor.getrgb("black"), font=self.font)
                else:
                    count = self.count_around(i, j)
                    if count == 0:
                        continue
                    font_size = self.font.getsize(str(count))
                    center = (80 * (i + 1) - (font_size[0] / 2) - 40, 80 * (j + 1) - 40 - (font_size[1] / 2))
                    draw.text(center, str(count), fill=self.__get_count_text_color(count), font=self.font)

    def __get_count_text_color(self, count):
        if count == 1:
            return ImageColor.getrgb("green")
        if count == 2:
            return ImageColor.getrgb("orange")
        if count == 3:
            return ImageColor.getrgb("red")
        if count == 4:
            return ImageColor.getrgb("darkred")
        return ImageColor.getrgb("black")

    def mine(self, row: int, column: int):
        if row > self.row or column > self.column or row < 0 or column < 0:
            raise ValueError("非法操作")
        cell = self.panel[row][column]
        if self.state == GameState.PREPARE:
            self.__gen_mine()
        if cell.is_mine:
            pass
            # todo 游戏结束

    def __gen_mine(self):
        count = 0
        while count < self.mines:
            row = random.randint(0, self.row - 1)
            column = random.randint(0, self.row - 1)
            if self.panel[row][column].is_mine:
                continue
            self.panel[row][column].is_mine = True
            count += 1

    def count_around(self, row: int, column: int) -> int:
        count = 0
        for r in range(row - 1, row + 1):
            for c in range(column - 1, column + 1):
                if self.panel[r][c].is_mine:
                    count += 1
        if self.panel[row][column].is_mine:
            count -= 1
        return count


if __name__ == '__main__':
    mine = MineSweeper(10, 10, 10)
    mine.mine(0, 0)
    mine.draw_panel().show()
