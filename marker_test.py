import numpy as np
import plotly.graph_objects as go




x = np.linspace(0,7,8)
y = np.linspace(0,7,8)

xx,yy = np.meshgrid(x,y)
xx.flatten()
base_coordinates = np.array([xx.flatten()[:53],yy.flatten()[:53]])



a = base_coordinates
b = base_coordinates +10
c = base_coordinates +20
d = base_coordinates +30

traces = [a,b,c,d]
invalid_markers =np.array([225, 226, 227, 228, 229, 230, 231, 232, 233, 234,235, 237,
                           238, 239, 240, 241, 242, 243, 244, 245,246, 247, 248, 249, 250, 251, 252,
                          325, 326, 327, 328, 329, 330, 331, 332, 333, 334,325, 326, 327,
                           328, 329, 330, 331, 332, 333, 334,325, 326, 327, 328, 329, 330, 331, 332, 333, 334,
                          335, 337, 338, 339, 340, 341, 342, 343, 344, 345,346, 347, 348, 349, 350, 351, 352])

base = np.array([x for x in range(0,53)])

markers = [base,base+100,base+200,base+300]
for i,m in enumerate(markers):
    markers[i] = np.where(np.in1d(m,invalid_markers),0,m)
markers


fig = go.Figure()
for i,t in enumerate(traces):
    fig.add_trace(go.Scatter(
        x = t[0],
        y = t[1],
        mode = "markers",
        marker = dict(symbol=markers[i],size = 7),
        text =[f"marker type: {x}" for x in markers[i]]
    ))

fig.show()