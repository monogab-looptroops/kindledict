
import jinja2
from jinja2 import Environment



# template = env.get_template("frame.html")


def create_file():
    #load template file
    templateLoader = jinja2.FileSystemLoader(searchpath="./")
    env = Environment(loader=templateLoader)
    t = env.get_template("frame.html")

    f = open("content_gen.html", "w")

    s = t.render(words=[{"nl":"appel", "hu":"alma"},{"nl":"moeder", "hu":"anyu"}])
    f.write(s)

    f.close()



if __name__ == "__main__":
    create_file()

