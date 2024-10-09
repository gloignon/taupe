import gradio as gr                                                             

def b_clicked(o):
    return gr.Button.update(interactive=True)
    

with gr.Blocks() as app:
    b = gr.Button("Enable the other obutton", interactive = True)
    o = gr.Button("Other Button", interactive = False)
    b.click(fn = b_clicked, inputs = b, outputs = o)

if __name__ == "__main__":
    app.launch()