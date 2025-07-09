import plotly.graph_objects as go

# to show plotly figures in quarto HTML file
import plotly.io as pio

psrc_color = ["#91268F", "#8CC63E", "#00A7A0", "#F05A28", "#4C4C4C", "#630460", "#9f3913", "#588527", "#00716c", "#3e4040"]

# psrc template
pio.templates["psrc_color"] = go.layout.Template(
    layout_colorway=psrc_color, layout_font=dict(size=11, family="Poppins")
)

pio.renderers.default = "plotly_mimetype+notebook_connected"
pio.templates.default = "simple_white+psrc_color" # set plotly template