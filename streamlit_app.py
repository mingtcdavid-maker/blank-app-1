import io
import re
from pathlib import Path

import requests
import streamlit as st
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

from website import compiledata

st.title("HDB Ops Survey Report Generator")

TEMPLATE_PATH = Path(__file__).parent / "HDB Ops Survey Report.pptx"

# TODO: replace with the deployed usage-logger API's base URL (see logger_api.py)
LOGGER_URL = "placeholder"

PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*(.*?)\s*\}\}")

# Maps the {{ tag }} text found in the template to the keys compiledata() returns
FIELD_ALIASES = {
    "block": "block_no",
    "street": "street_name",
    "nearest hydrant": "nearest_hydrant",
    "number of breaching": "number_breaching",
}

# Uploaded-photo fields from compiledata(), and the heading each gets its own slide(s) under
PHOTO_FIELDS = [
    ("pic_best_appliance", "Best Appliance Placement"),
    ("pic_nearest_hydrant", "Nearest Hydrant"),
    ("pic_nearest_breaching", "Nearest Breaching Inlet"),
]

PHOTOS_PER_SLIDE = 4
PHOTO_COLUMNS = 2


def main():
    data = compiledata()
    if data:
        createppt()
        compileppt(data)
        downloadppt()
        stats = logusage()
        display_usage_stats(stats)

    st.sidebar.header("Usage stats")
    if st.sidebar.button("Refresh usage stats"):
        display_usage_stats(get_usage_stats())


def createppt():
    """Load the HDB Ops Survey Report template so compileppt() can fill it in."""
    prs = Presentation(TEMPLATE_PATH)
    st.session_state.prs = prs
    return prs


def compileppt(data):
    """Replace the {{ }} placeholders in the loaded template with survey data and append photo slides."""
    prs = st.session_state.prs

    for slide in prs.slides:
        for shape in slide.shapes:
            _substitute_shape(shape, data)

    for field, heading in PHOTO_FIELDS:
        _add_photo_slides(prs, heading, data.get(field) or [])

    return prs


def downloadppt():
    """Serialize the compiled presentation and offer it to the user as a download."""
    prs = st.session_state.prs
    buffer = io.BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    st.download_button(
        label="Download HDB Ops Survey Report",
        data=buffer,
        file_name="HDB Ops Survey Report - Completed.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    return buffer


def logusage():
    """Tell the usage-logger API a report was generated and return the updated totals."""
    try:
        response = requests.post(f"{LOGGER_URL}/usage", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.warning(f"Could not reach usage logger: {exc}")
        return None


def get_usage_stats():
    """Fetch current usage totals from the usage-logger API without recording a new use."""
    try:
        response = requests.get(f"{LOGGER_URL}/usage", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.sidebar.warning(f"Could not reach usage logger: {exc}")
        return None


def display_usage_stats(stats):
    if not stats:
        return
    st.sidebar.metric("Reports generated", stats["count"])
    st.sidebar.metric("Est. hours saved", stats["hours_saved"])


def _format_value(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value) if value is not None else ""


def _resolve_placeholder(tag, data):
    key = FIELD_ALIASES.get(tag, tag)
    return _format_value(data.get(key, ""))


def _substitute_text_frame(text_frame, data):
    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            if "{{" in run.text:
                run.text = PLACEHOLDER_PATTERN.sub(lambda m: _resolve_placeholder(m.group(1), data), run.text)


def _substitute_shape(shape, data):
    if shape.has_text_frame:
        _substitute_text_frame(shape.text_frame, data)
    if shape.has_table:
        for row in shape.table.rows:
            for cell in row.cells:
                _substitute_text_frame(cell.text_frame, data)
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        for sub_shape in shape.shapes:
            _substitute_shape(sub_shape, data)


def _fit_dimensions(image_file, max_width, max_height):
    image_file.seek(0)
    with Image.open(image_file) as img:
        width_px, height_px = img.size
    image_file.seek(0)
    scale = min(max_width / width_px, max_height / height_px)
    return int(width_px * scale), int(height_px * scale)


def _add_photo_slides(prs, heading, uploaded_files):
    if not uploaded_files:
        return

    layout = prs.slide_layouts[5]  # "Title Only"
    margin = Inches(0.4)
    content_top = Inches(1.4)
    usable_width = prs.slide_width - 2 * margin
    usable_height = prs.slide_height - content_top - margin
    max_rows = 2
    cell_width = int((usable_width - margin * (PHOTO_COLUMNS - 1)) / PHOTO_COLUMNS)
    cell_height = int((usable_height - margin * (max_rows - 1)) / max_rows)

    for chunk_start in range(0, len(uploaded_files), PHOTOS_PER_SLIDE):
        chunk = uploaded_files[chunk_start:chunk_start + PHOTOS_PER_SLIDE]
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = heading

        for i, image_file in enumerate(chunk):
            row, col = divmod(i, PHOTO_COLUMNS)
            cell_left = margin + col * (cell_width + margin)
            cell_top = content_top + row * (cell_height + margin)

            width, height = _fit_dimensions(image_file, cell_width, cell_height)
            left = cell_left + (cell_width - width) // 2
            top = cell_top + (cell_height - height) // 2

            image_file.seek(0)
            slide.shapes.add_picture(image_file, left, top, width=width, height=height)


if __name__ == "__main__":
    main()
