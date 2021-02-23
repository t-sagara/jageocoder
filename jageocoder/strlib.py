import re

class Strlib(object):

    def __init__(self):
        self.hyphen = "-－\u2010\u002D\u00AD\u2011\u2043"
        self.kansuji = "〇一二三四五六七八九"
        self.arabic = "０１２３４５６７８９"

        self.re_en = re.compile(r'[a-zA-Z]')
        self.re_ascii = re.compile(r'[\u0021-\u007e]')
        self.re_hira = re.compile(r'[\u3041-\u309F]')
        self.re_kata = re.compile(r'[\u30A1-\u30FF]')
        self.re_cjk = re.compile(r'[\u4E00-\u9FFF]')

    def is_hyphen(self, c):
        return (c in self.hyphen)

    def is_kansuji(self, c):
        return (c in self.kansuji)

    def is_arabic_number(self, c):
        return (c in self.arabic)

    def get_numeric_char(self, c):
        
        pos = '0123456789'.find(c)
        if pos >= 0:
            return pos
        
        pos = self.kansuji.find(c)
        if pos >= 0:
            return pos

        pos = self.arabic.find(c)
        if pos >= 0:
            return pos

        if c == '十':
            return 10

        if c == '百':
            return 100

        if c == '千':
            return 1000

        if c == '万':
            return 10000

        return False

    def get_number(self, string):
        total = 0
        curval = 0
        mode = -1   # -1: unset, 0: parsing arabic, 1: parsing kansuji

        l = 0
        for i, c in enumerate(string):
            if c in '0123456789' or self.is_arabic_number(c):
                k = self.get_numeric_char(c)
                curval = curval * 10 + k
                mode = 0
                l += 1

            elif mode == 0:
                break

            elif self.is_kansuji(c):
                k = self.get_numeric_char(c)
                if total + curval == 0 and k == 0:
                    break

                curval = curval * 10 + k
                mode = 1
                l += 1
            elif c in '十百千万':
                k = self.get_numeric_char(c)
                curval = 1 if curval == 0 else curval
                total = total * k if total % k > 0 else total
                total += curval * k
                curval = 0
                mode = 1
                l += 1

            else:
                break

        total += curval
        return {"n": total, "i":l}

    def get_ctype(self, c):
        if self.re_hira.match(c):
            return 4  # ひらがな
        elif self.re_kata.match(c):
            return 5  # カタカナ
        elif self.re_en.match(c):
            return 6  # 半角アルファベット
        elif self.re_ascii.match(c):
            return 0  # アスキー文字
        elif c in self.arabic or c in self.kansuji:
            return 2  # 数字
        elif self.re_cjk.match(c):
            return 1  # 漢字

        return -1  #不明

strlib = Strlib() # singleton
        
