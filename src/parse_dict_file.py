from functools import reduce



def parse_file(filename):
    with open(filename) as f:
        lines = f.readlines()

        dict = []
        for line in lines:
            line = line.strip()
            if line == "":
                continue

            if line.startswith('#'):
                continue

            isExample = line.strip().startswith('[') and line.strip().endswith(']')
            if isExample:
                line = line.strip("[]")

            ws = line.split("-")

            if len(ws) > 2:
                wsr = []
                wsr.append( ws[0] )
                wsr.append( reduce(lambda a, b: a +"-"+ b, ws[1:]))
                ws = wsr
            ws = [w.strip() for w in ws]

            if len(ws)<2:
                print("strange line", line)
                continue
            word = {"nl": ws[0], "hu": ws[1]}
            if isExample:
                dict[len(dict)-1]["example"] = line
            else:
                dict.append(word)

        return dict



if __name__ == "__main__":
    import os

    cwd = os.getcwd()
    print(cwd)
    dict = parse_file("../neo4j/test")
    print(dict)
