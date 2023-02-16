
from src.parse_dict_file import parse_file
import os
def parse_folder(foldername):
    dict = []
    for file in os.listdir(foldername):
        dict = dict + parse_file(foldername+file)

    print(dict)
    print("length", len(dict))
    return dict


if __name__ == "__main__":


    cwd = os.getcwd()
    print(cwd)
    parse_folder(cwd+'/../neo4j/')



    #
