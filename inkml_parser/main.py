from inkml_parser.inkml_render import get_traces_data, inkml2img
from inkml_parser.inkml_util import get_max_dimensions

x, y = get_max_dimensions("tmp.inkml")

# var
# pixel = (himetric * dpi) / 2540;
#
# // XPS
# DPI = 141.21
# // Himetric
# max = 32767
# // Pixels = 32767 * 141.21 / 2540

x = x * 141.21 / 2540 / 2
y = y * 141.21 / 2540 / 2

print(f"{x} {y}")
