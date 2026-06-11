#!/usr/bin/env python3
"""Genera landing-calculadoras-wpbakery.txt a partir de landing-calculadoras.html.

WPBakery guarda el contenido de los elementos "Raw HTML" como
base64(rawurlencode(html)), así que no se puede editar a mano dentro del
shortcode. Si cambias algo en landing-calculadoras.html (agregar una
calculadora, una sección, etc.), vuelve a correr:  python3 generar-wpbakery.py
y pega de nuevo el contenido del .txt en la página.
"""
import base64
import re
import urllib.parse

SRC = "landing-calculadoras.html"
OUT = "landing-calculadoras-wpbakery.txt"

# CSS de las tarjetas, re-escopado a .cbt-card (en WPBakery la rejilla la dan
# las columnas del builder, ya no existe el contenedor .cbt-landing).
CARD_CSS = """<style>
  /* ── Landing de calculadoras · Carbotecnia · estilos de tarjeta ── */
  .cbt-card, .cbt-card *, .cbt-card *::before, .cbt-card *::after { box-sizing: border-box; }
  .cbt-card {
    font-family: 'Inter', -apple-system, "Segoe UI", sans-serif;
    color: #2a3440;
    background: #ffffff;
    border: 1.5px solid var(--c);
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(20, 30, 40, 0.06);
  }
  .cbt-card .cbt-banda {
    display: flex;
    align-items: center;
    gap: 11px;
    background: var(--c);
    color: #ffffff;
    padding: 10px 18px;
  }
  .cbt-card .cbt-banda-icono { display: grid; place-items: center; flex-shrink: 0; }
  .cbt-card h3.cbt-card-titulo {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 17px;
    line-height: 1.25;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #ffffff;
    margin: 0;
    padding: 0;
  }
  .cbt-card .cbt-card-body {
    display: flex;
    gap: 18px;
    padding: 18px 20px 20px;
  }
  .cbt-card .cbt-card-main { flex: 1; min-width: 0; }
  .cbt-card .cbt-card-desc {
    font-size: 14px;
    line-height: 1.55;
    color: #5a6573;
    margin: 0 0 10px;
  }
  .cbt-card .cbt-media {
    width: 112px;
    height: 112px;
    flex-shrink: 0;
    border-radius: 8px;
    background: var(--cs);
    border: 1.5px dashed color-mix(in srgb, var(--c) 35%, #ffffff);
    color: var(--c);
    display: grid;
    place-items: center;
    align-content: center;
    gap: 6px;
    opacity: 0.85;
    overflow: hidden;
  }
  .cbt-card .cbt-media span { font-size: 11px; font-weight: 500; opacity: 0.75; }
  /* La imagen NUNCA puede crecer más que su recuadro, aunque el tema
     o un plugin de lazy-load intenten poner height:auto */
  .cbt-card .cbt-img {
    width: 112px !important;
    height: 112px !important;
    max-width: 112px !important;
    max-height: 112px !important;
    flex-shrink: 0;
    border-radius: 8px;
    object-fit: cover !important;
    display: block;
    margin: 0 !important;
  }
  /* Si la imagen quedó dentro del recuadro .cbt-media, que lo llene exacto */
  .cbt-card .cbt-media:has(.cbt-img) { border: none; background: none; opacity: 1; }
  .cbt-card .cbt-media .cbt-img {
    width: 100% !important;
    height: 100% !important;
    max-width: 100% !important;
    max-height: 100% !important;
  }
  .cbt-card ul.cbt-lista {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .cbt-card .cbt-lista li { margin: 0; padding: 0; border-top: 1px solid #eef1f4; }
  .cbt-card .cbt-lista li:first-child { border-top: none; }
  .cbt-card .cbt-lista a {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 8px 2px;
    font-family: 'Outfit', sans-serif;
    font-size: 14.5px;
    font-weight: 600;
    line-height: 1.4;
    color: var(--c);
    text-decoration: none;
    box-shadow: none;
  }
  .cbt-card .cbt-lista a::before {
    content: "";
    width: 12px;
    height: 12px;
    flex-shrink: 0;
    background-color: var(--c);
    -webkit-mask: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>') center / contain no-repeat;
    mask: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>') center / contain no-repeat;
  }
  .cbt-card .cbt-lista a:hover {
    color: var(--c);
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  @media (max-width: 480px) {
    .cbt-card .cbt-card-body { flex-direction: column; }
    .cbt-card .cbt-media { width: 100%; height: 96px; }
    .cbt-card .cbt-img {
      width: 100% !important;
      height: 96px !important;
      max-width: 100% !important;
      max-height: 96px !important;
    }
    .cbt-card .cbt-media .cbt-img { height: 100% !important; max-height: 100% !important; }
  }
</style>"""

TITULO = "Calculadoras y herramientas"
INTRO = ("Herramientas de cálculo y diagnóstico para tratamiento de agua y aire: "
         "dimensionamiento de equipos, dosificación, normatividad y conversiones. "
         "Selecciona una categoría y abre la herramienta que necesitas.")


def raw_html(html: str) -> str:
    """Codifica como lo espera [vc_raw_html]: base64(rawurlencode(html))."""
    encoded = urllib.parse.quote(html, safe="")
    return base64.b64encode(encoded.encode()).decode()


COLUMN_INNER = (
    '[vc_column_inner column_padding="no-extra-padding" column_padding_tablet="inherit" '
    'column_padding_phone="inherit" column_padding_position="all" '
    'column_element_spacing="default" background_color_opacity="1" '
    'background_hover_color_opacity="1" column_shadow="none" column_border_radius="none" '
    'column_link_target="_self" overflow="visible" gradient_direction="left_to_right" '
    'overlay_strength="0.3" width="{w}" tablet_width_inherit="default" '
    'animation_type="default" bg_image_animation="none" border_type="simple" '
    'column_border_width="none" column_border_style="solid"]{contenido}[/vc_column_inner]'
)

ROW_INNER = (
    '[vc_row_inner column_margin="default" column_direction="default" '
    'column_direction_tablet="default" column_direction_phone="default" '
    'text_align="left" row_position="default" row_position_tablet="inherit" '
    'row_position_phone="inherit" overflow="visible" pointer_events="all"]'
    '{columnas}[/vc_row_inner]'
)


def main():
    html = open(SRC, encoding="utf-8").read()
    # Solo las secciones reales (con style="--c:..."), no las de los comentarios.
    cards = re.findall(r'<section class="cbt-card" style="--c:.*?</section>', html, re.S)
    assert len(cards) == 8, f"esperaba 8 secciones, encontré {len(cards)}"
    # Quitar la sangría común del archivo fuente.
    cards = [re.sub(r"^    ", "", c, flags=re.M) for c in cards]

    partes = []

    # Fila exterior (en contenedor, fondo blanco)
    partes.append(
        '[vc_row type="in_container" full_screen_row_position="middle" '
        'column_margin="default" column_direction="default" '
        'column_direction_tablet="default" column_direction_phone="default" '
        'bg_color="#ffffff" scene_position="center" top_padding="40" '
        'bottom_padding="56" text_color="dark" text_align="left" '
        'row_border_radius="none" row_border_radius_applies="bg" '
        'row_position_desktop="default" row_position_tablet="inherit" '
        'row_position_phone="inherit" overflow="visible" overlay_strength="0.3" '
        'gradient_direction="left_to_right" shape_divider_position="bottom" '
        'bg_image_animation="none"]'
        '[vc_column column_padding="no-extra-padding" column_padding_tablet="inherit" '
        'column_padding_phone="inherit" column_padding_position="all" '
        'column_element_spacing="default" background_color_opacity="1" '
        'background_hover_color_opacity="1" column_shadow="none" '
        'column_border_radius="none" column_link_target="_self" '
        'column_position="default" gradient_direction="left_to_right" '
        'overlay_strength="0.3" width="1/1" tablet_width_inherit="default" '
        'animation_type="default" bg_image_animation="none" border_type="simple" '
        'column_border_width="none" column_border_style="solid"]'
    )

    # Estilos de las tarjetas (Raw HTML invisible)
    partes.append(ROW_INNER.format(columnas=COLUMN_INNER.format(
        w="1/1", contenido=f"[vc_raw_html]{raw_html(CARD_CSS)}[/vc_raw_html]")))

    # Título e introducción
    partes.append(ROW_INNER.format(columnas=COLUMN_INNER.format(
        w="1/1",
        contenido=(
            f'[vc_custom_heading text="{TITULO}" '
            'font_container="tag:h2|font_size:34px|text_align:center|line_height:1.15" '
            'use_theme_fonts="yes" css_animation="none"]'
            f'[vc_custom_heading text="{INTRO}" '
            'font_container="tag:p|font_size:16px|text_align:center|line_height:1.6|color:%234b5663" '
            'use_theme_fonts="yes" css_animation="none"]'
        ))))

    # Rejilla: 4 filas de 2 tarjetas (1/2 + 1/2)
    for i in range(0, len(cards), 2):
        cols = "".join(
            COLUMN_INNER.format(w="1/2", contenido=f"[vc_raw_html]{raw_html(c)}[/vc_raw_html]")
            for c in cards[i:i + 2]
        )
        partes.append(ROW_INNER.format(columnas=cols))

    partes.append("[/vc_column][/vc_row]")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("".join(partes) + "\n")
    print(f"OK → {OUT}")


if __name__ == "__main__":
    main()
