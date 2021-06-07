

from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
    loader=PackageLoader("words"),
    autoescape=select_autoescape()
)
template = env.get_template("frame.html")

def create_file():



    f = open("content_gen.html", "w")

    f.write(template.render([{"nl":"appel", "hu":"alma"}]))
    f.close()



if __name__ == "__main__":
    create_file()

