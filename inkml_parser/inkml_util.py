from bs4 import BeautifulSoup


def get_max_dimensions(filename):
    file = open(filename, "r")
    soup = BeautifulSoup(file.read(), "xml")
    root = soup.find_all("inkml:ink")[0]
    brushes = {}
    max_x = 0
    max_y = 0

    # for brush_roots in root.definitions.find_all("inkml:brush"):
    #     id = brush_roots['xml:id']
    #
    #     properties = {}
    #
    #     for brushProperty in brush_roots.find_all("inkml:brushProperty"):
    #         propertyName = brushProperty['name']
    #         propertyValue = brushProperty['value']
    #
    #         properties[propertyName] = propertyValue
    #
    #     brushes[id] = properties

    for inktrace in root.find("inkml:traceGroup").find_all("inkml:trace"):
        # id = inktrace['xml:id']
        # brushRef = inktrace['brushRef']
        # contextRef = inktrace['contextRef']

        values = inktrace.get_text().split(",")
        values = [value.strip() for value in values]
        values = [value.split(" ") for value in values]

        # string = 'var canvas = document.getElementById(\"Canvas1\");\n' \
        #          'var context = canvas.getContext("2d");\n'
        # index = 0
        for value_set in values:
            X = int(value_set[0])
            Y = int(value_set[1])
            if X > max_x:
                max_x = X

            if Y > max_y:
                max_y = Y

        #     if index == 0:
        #         string += f"context.moveTo({X}, {Y});\n"
        #         index += 1
        #     else:
        #         string += f"context.lineTo({X}, {Y});\n"
        #
        # string += "context.stroke();\n\n\n"
        #
        # output_js += string

    # with open("render.js", "w") as file:
    #     file.write(output_js)

    return max_x, max_y
