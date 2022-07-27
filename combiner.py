from contextlib import ExitStack
from os.path import exists
from typing import Dict, Any, Optional

import PySimpleGUI as sg
import PIL
from PIL import Image, ImageOps

# On Linux/MacOS:
#   python3 -m pip install PySimpleGui Pillow
#   apt install python3-tk
#   python3 combiner.py
#
# On Windows:
#   Download Python 3 for Windows: https://www.python.org/downloads/windows/
#   Do the thing.


class Images(object):
    metallic_img: Optional[Image.Image]
    smoothness_img: Optional[Image.Image]

    def __init__(self, metallic_file: str, smoothness_file: str):
        self.metallic_file = metallic_file
        self.smoothness_file = smoothness_file
        self.metallic_img = None
        self.smoothness_img = None

    def open(self):
        self.stack = ExitStack()
        if self.metallic_file:
            self.metallic_img = self.stack.enter_context(
                Image.open(self.metallic_file))
        if self.smoothness_file:
            self.smoothness_img = self.stack.enter_context(
                Image.open(self.smoothness_file))

    def close(self):
        self.stack.close()

    def __enter__(self):
        self.open()
        return (self.metallic_img, self.smoothness_img)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def combine(metallic_img: Image.Image, smoothness_img: Image.Image,
            is_rough: bool) -> Image.Image:
    """Combines metallic and smoothness textures into combined texture.

    If is_rough is set, then the smoothness texture is actually a
    roughness texture, and it will be converted to smoothness by inversion.

    Metallic maps to R and smoothness maps to A. Each are treated as
    grayscale.
    """
    metallic_gray = ImageOps.grayscale(metallic_img).getchannel("L")
    smoothness_gray = ImageOps.grayscale(smoothness_img).getchannel("L")
    if is_rough:
        smoothness_gray = ImageOps.invert(smoothness_gray)
    zero = Image.new("L", metallic_gray.size)
    return Image.merge("RGBA", [metallic_gray, zero, zero, smoothness_gray])


USE_COLOR: int = 0
USE_SOLID: int = 1


def process(values: Dict[str, Any]) -> bool:
    metallic = values["metallic"].strip()
    is_nonmetallic = values["non-metallic"]
    smoothness = values["smoothness"].strip()
    is_rough = not values["smooth"]
    save_file = values["saveas"].strip()
    mode = USE_SOLID if values["solid"] else USE_COLOR

    if save_file == "":
        sg.popup("You need to specify a save file!", title="Oops")
        return False
    # print(f"Metallic: {metallic}, roughness: {roughness}, rough: {is_rough}")
    if metallic == "" and not is_nonmetallic:
        sg.popup("You need to specify a metallic file (or check Non-metallic)!",
                 title="Oops")
        return False
    if mode == USE_COLOR and smoothness == "":
        sg.popup("You need to specify a roughness/smoothness file!",
                 title="Oops")
        return False
    if mode == USE_SOLID and is_nonmetallic:
        sg.popup(
            "You need to specify at least a metallic file or a "
            "roughness/smoothness file!",
            title="Oops")
        return False
    if is_nonmetallic:
        metallic = ""
    if mode == USE_SOLID:
        smoothness = ""

    image: Image.Image

    try:
        with Images(metallic, smoothness) as (metallic_img, smoothness_img):
            if metallic_img is None:
                metallic_img = Image.new("L", smoothness_img.size)
            if smoothness_img is None:
                smoothness_img = Image.new("L", metallic_img.size)
                smoothness_img = ImageOps.invert(smoothness_img)  # All one
            image = combine(metallic_img, smoothness_img, is_rough)
    except FileNotFoundError as e:
        sg.popup(f"File not found: {e.filename}", title="File not found")
        return False
    except PIL.UnidentifiedImageError as e:
        sg.popup(f"Not an image: {e.filename}", title="Not an image")
        return False

    if exists(save_file):
        choice, _ = sg.Window("Really?",
                              [[sg.T("Overwrite existing file?")],
                               [sg.Yes(s=10), sg.No(s=10)]],
                              disable_close=True).read(close=True)
        if not choice:
            return False

    image.save(save_file)
    return True


def main() -> None:
    layout = [[sg.Text("Metallic map file:")],
              [
                  sg.In(key="metallic"),
                  sg.FileBrowse(),
                  sg.Checkbox("Non-metallic", key="non-metallic"),
              ], 
              [sg.Text("Roughness/smoothness map file:")],
              [
                  sg.In(key="smoothness"),
                  sg.FileBrowse(),
                  sg.Checkbox("Smoothness", key="smooth"),
                  sg.Checkbox("All solid", key="solid"),
              ],
              [
                  sg.In(default_text="output.png", key="saveas"),
                  sg.FileSaveAs(default_extension=".png")
              ], 
              [sg.Submit("Go!", key="submit"),
                  sg.Cancel(key="cancel")]]

    window = sg.Window("Neos combiner thing", layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "cancel":
            break
        if event == "submit":
            if process(values):
                break
    window.close()


if __name__ == "__main__":
    main()
