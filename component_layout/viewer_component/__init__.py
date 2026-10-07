import os
import streamlit.components.v1 as components

_component = components.declare_component(
    "parasitic_2027_viewer",
    path=os.path.dirname(__file__),
)

def viewer_component(
    image_b64: str,
    viewport: int,
    init_zoom: float,
    init_panX: float,
    init_panY: float,
    theme_mode: str = "System",
    key: str = "microscopy_viewer",
    image_id: str = "",
):
    """
    Use viewport=0 for browser-width auto sizing.

    Returns dict ONLY when user presses Calculate on canvas:
      {
        "action": "calculate",
        "calc_token": "<unique>",
        "zoom": float,
        "panX": float,
        "panY": float,
        "viewport": int
      }
    Otherwise returns None.
    """
    return _component(
        image_b64=image_b64,
        viewport=viewport,
        init_zoom=init_zoom,
        init_panX=init_panX,
        init_panY=init_panY,
        theme_mode=theme_mode,
        image_id=image_id,
        key=key,
        default=None,
    )
