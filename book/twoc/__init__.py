import plotly.io as pio
colors = dict(
    bigblue = "#1D4EF5",
    paleblue = "#F2F5FC",
    midnight = "#230344",
    mauve = "#B86BFC",
    forest = "#057761",
    lightgreen = "#0CEFAE",
    magenta = "#C60A76",
    pink = "#FF808B",
    coral = "#FF4E4F",
    yellow = "#FFDE17",
)
pio.templates.default = "plotly_white"
custom_template = pio.templates["plotly_white"].layout.template
custom_template.layout.update(plot_bgcolor=colors["paleblue"], paper_bgcolor=colors["paleblue"])
custom_template.layout.colorway = [colors["bigblue"], colors["coral"], colors["lightgreen"], colors["magenta"], colors["pink"], colors["yellow"]]
pio.templates["custom_theme"] = custom_template
pio.templates.default = "custom_theme"