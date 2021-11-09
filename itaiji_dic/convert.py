import json
import os

itaiji_dic_json = os.path.join(
    os.path.dirname(__file__), '../jageocoder/itaiji_dic.json')
itaiji_src_json = os.path.join(
    os.path.dirname(__file__), 'itaiji_src.json')


def recover_dictionary():

    with open(itaiji_dic_json, 'r', encoding='utf-8') as f:
        itaiji_dic = json.load(f)

    dic = {}
    for src, dst in itaiji_dic.items():
        if dst in dic:
            dic[dst].append(src)
        else:
            dic[dst] = [src]

    new_dic = {}
    for dst, chars in dic.items():
        src = chars
        new_dic[dst] = ''.join(src)

    with open(itaiji_src_json, 'w', encoding='utf-8') as f:
        f.write("{\n")
        c = 0
        for dst, chars in new_dic.items():
            if c > 0:
                print(',', file=f, end="\n")

            print('  "{}": "{}"'.format(dst, chars), file=f, end='')
            c += 1

        f.write("\n}\n")


def create_dictionary():

    with open(itaiji_src_json, 'r', encoding='utf-8') as f:
        dic = json.load(f)

    itaiji_dic = {}
    for dst, chars in dic.items():
        for char in chars:
            itaiji_dic[char] = dst

    with open(itaiji_dic_json, 'w', encoding='utf-8') as f:
        f.write(json.dumps(itaiji_dic, ensure_ascii=True))


if __name__ == '__main__':
    create_dictionary()
    # recover_dictionary()
