def draw_wrapped_text(pdf, text, x, y, max_width, line_height=15):

    words = text.split()

    line = ""

    for word in words:

        if pdf.stringWidth(line + word + " ", "Helvetica", 12) <= max_width:

            line += word + " "

        else:

            pdf.drawString(x, y, line.strip())

            y -= line_height

            line = word + " "


    if line:

        pdf.drawString(x, y, line.strip())

        y -= line_height


    return y

