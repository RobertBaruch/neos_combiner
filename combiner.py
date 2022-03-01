from os.path import exists
from typing import Dict, Any

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


def combine(metallic_img: Image, smoothness_img: Image,
            is_rough: bool) -> Image:
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
    smoothness = values["smoothness"].strip()
    is_rough = not values["smooth"]
    save_file = values["saveas"].strip()
    mode = USE_SOLID if values["solid"] else USE_COLOR

    if save_file == "":
        sg.popup("You need to specify a save file!", title="Oops")
        return False
    # print(f"Metallic: {metallic}, roughness: {roughness}, rough: {is_rough}")
    if metallic == "":
        sg.popup("You need to specify a metallic file!", title="Oops")
        return False
    if mode == USE_COLOR and smoothness == "":
        sg.popup("You need to specify a roughness/smoothness file!",
                 title="Oops")
        return False

    image: Image

    try:
        with Image.open(metallic) as metallic_img:
            if mode == USE_COLOR:
                try:
                    with Image.open(smoothness) as smoothness_img:
                        if metallic_img.size != smoothness_img.size:
                            sg.popup("Images are not the same size",
                                     title="Oops")
                            return False
                        image = combine(metallic_img, smoothness_img, is_rough)
                except FileNotFoundError:
                    sg.popup(f"Failed to find file {smoothness}", title="Oops")
                    return False
                except PIL.UnidentifiedImageError:
                    sg.popup(f"Failed to identify {smoothness} as an image",
                             title="Oops")
                    return False
            else:
                solid = Image.new("L", metallic_img.size)
                solid = ImageOps.invert(solid)  # All one
                image = combine(metallic_img, solid, is_rough)

    except FileNotFoundError:
        sg.popup(f"Failed to find file {metallic}", title="Oops")
        return False
    except PIL.UnidentifiedImageError:
        sg.popup(f"Failed to identify {metallic} as an image", title="Oops")
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
              [sg.In(key="metallic"), sg.FileBrowse()],
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
              ], [sg.Submit("Go!", key="submit"),
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
