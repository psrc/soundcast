import plotly.io as pio
import plotly.graph_objects as go
import os
import toml

config = toml.load(os.path.join(os.getcwd(), '..\\..\\..\\..\\configuration', 'validation_configuration.toml'))

# psrc template
pio.templates["psrc_color"] = go.layout.Template(
    layout_colorway=config['psrc_color'],
    layout_font=dict(size=11, family="Poppins")
)
