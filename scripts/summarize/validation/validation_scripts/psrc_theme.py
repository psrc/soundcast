import plotly.io as pio
import plotly.graph_objects as go
import os
import toml

#config = toml.load(os.path.join(os.getcwd(), 'validation_configuration.toml'))
config = toml.load(r'C:\Workspace\travel-modeling\estimation\validation_configuration.toml')

# psrc template
pio.templates["psrc_color"] = go.layout.Template(
    layout_colorway=config['psrc_color'],
    layout_font=dict(size=11, family="Poppins")
)
