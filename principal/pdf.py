from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf_response(request, plantilla, contexto, nombre_archivo):
    html = render_to_string(plantilla, contexto, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()
    respuesta = HttpResponse(pdf, content_type='application/pdf')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return respuesta
