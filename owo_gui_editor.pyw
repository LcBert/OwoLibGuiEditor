import tkinter as tk
from tkinter import filedialog, messagebox
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

# =====================================================================
# FUNZIONE DI UTILITY PER IL COMFORT DEL TYPE-CHECKER
# =====================================================================
def safe_text(node: ET.Element | None, default: str = "0") -> str:
    """Garantisce al type-checker che il valore restituito sia sempre una str"""
    if node is not None and node.text is not None:
        return node.text
    return default

# =====================================================================
# MODELLI DI STRUTTURA DATI CONFORMI ALL'XSD DI OωO-LIB
# =====================================================================

class UIComponent:
    def __init__(self, comp_id, comp_type="button", text=""):
        self.id = comp_id
        self.type = comp_type # 'button', 'label'
        self.text = text
        self.parent = None
        
        # Annotazione esplicita per evitare rigidità del type-checker
        self.bounds: tuple[int, int, int, int] = (0, 0, 0, 0)
        
        # Sizing ufficiale oωo-lib basato su sotto-tag e attributo method dell'XSD
        self.width_method = "content"   # 'content', 'fill', 'fixed'
        self.width_value = "100"
        self.height_method = "content"  # 'content', 'fill', 'fixed'
        self.height_value = "20"
        
        # Gestione del Padding per Faccia
        self.padding_type = "all"       # 'all' oppure 'individual'
        self.padding_all = "0"
        self.padding_top = "0"
        self.padding_bottom = "0"
        self.padding_left = "0"
        self.padding_right = "0"
        
        # Gestione dei Margini per Faccia
        self.margins_type = "all"       # 'all' oppure 'individual'
        self.margins_all = "0"
        self.margins_top = "0"
        self.margins_bottom = "0"
        self.margins_left = "0"
        self.margins_right = "0"
        
        # Proprietà specifiche per etichette (label)
        self.label_shadow = "false"
        self.label_max_width = ""

        # Proprietà specifiche per text-box
        self.text_box_max_length = ""

        # Proprietà specifiche per text-area
        self.text_area_max_length = ""
        self.text_area_max_lines = ""
        self.text_area_display_char_count = "false"

        # Proprietà specifiche per box
        self.box_color_mode = "single"
        self.box_color = ""
        self.box_start_color = ""
        self.box_end_color = ""
        self.box_fill = "false"
        self.box_direction = "top-to-bottom"

        # Proprietà specifiche per spacer
        self.spacer_percent = ""

class UILayout(UIComponent):
    def __init__(self, comp_id, layout_type="Flow Layout", rows="2", cols="2", direction="vertical"):
        super().__init__(comp_id, comp_type="layout")
        self.layout_type = layout_type 
        self.rows = rows
        self.cols = cols
        self.direction = direction     # "vertical" oppure "horizontal"
        self.expanded = "true"         
        self.children = []
        
        # I layout di default riempiono lo spazio assegnato
        self.width_method = "fill"
        self.width_value = "100"
        self.height_method = "fill"
        self.height_value = "100"
        
        self.padding_type = "all"
        self.padding_all = "10"
        
        self.margins_type = "all"
        self.margins_all = "0"
        
        self.horiz_align = "center"
        self.vert_align = "center"
        self.surface_type = "panel-dark" 

    def add_child(self, child):
        if child.parent:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)
        return True

    def remove_child(self, child):
        if child in self.children:
            self.children.remove(child)
            child.parent = None

# =====================================================================
# APPLICAZIONE IDE DESIGNER COMPLETA (NEOFORGE 1.21.1)
# =====================================================================

class OwoQtDesigner:
    def __init__(self, root):
        self.root = root
        self.root.title("oωo-lib UI Advanced Designer (NeoForge 1.21.1)")
        self.root.geometry("1350x955")
        
        # Memorizza il percorso completo del file caricato o salvato
        self.current_file_path = None
        
        # Configurazione iniziale del layout principale sbloccato
        self.main_layout = UILayout("root_flow", "Flow Layout", direction="vertical")
        self.main_layout.surface_type = "vanilla-translucent"
        self.selected_component = self.main_layout
        
        self.layout_counter = 1
        self.widget_counter = 1
        self.dragged_component = None
        self.drag_proxy = None
        
        self.start_x = 0
        self.start_y = 0
        self.is_dragging = False

        self.setup_style()
        self.create_left_toolbox()
        self.create_center_viewport()
        self.create_right_property_panel()
        
        # Mostra le proprietà del root_flow all'avvio
        self.show_property_editor(self.main_layout)
        self.rebuild_and_snap()

    def setup_style(self):
        self.bg_dark = "#1e1e1e"
        self.bg_panel = "#2d2d2d"
        self.fg_light = "#ffffff"
        self.accent_blue = "#2196F3"
        self.root.configure(bg=self.bg_dark)

    def create_left_toolbox(self):
        toolbox = tk.Frame(self.root, width=260, bg=self.bg_panel, bd=1, relief=tk.SOLID)
        toolbox.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(toolbox, text="Widget Box (oωo-lib)", fg=self.fg_light, bg=self.bg_panel, font=("Arial", 11, "bold")).pack(pady=10)
        
        tk.Label(toolbox, text="Progetto", fg="gray", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, padx=10, pady=2)
        tk.Button(toolbox, text="📂 Importa XML", bg="#FF9800", fg="white", command=self.import_xml).pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="💾 Esporta XML Valido", bg="#4CAF50", fg="white", command=self.export_xml).pack(fill=tk.X, padx=15, pady=2)
        
        # Container fisso per i controlli del template
        self.template_control_container = tk.Frame(toolbox, bg=self.bg_panel)
        self.template_control_container.pack(fill=tk.X, padx=15, pady=4)

        self.prop_export_template = tk.BooleanVar(value=False)
        self.template_check = tk.Checkbutton(
            self.template_control_container, text="Esporta come Template", 
            variable=self.prop_export_template,
            bg=self.bg_panel, fg="#2196F3", selectcolor="#1e1e1e",
            activebackground=self.bg_panel, activeforeground="white",
            font=("Arial", 9, "bold"),
            command=self.toggle_template_name_visibility
        )
        self.template_check.pack(anchor=tk.W, pady=2)
        
        # Sottomenu di testo per il nome del template
        self.template_name_frame = tk.Frame(self.template_control_container, bg=self.bg_panel)
        tk.Label(self.template_name_frame, text="Nome Template (name):", fg="white", bg=self.bg_panel, font=("Arial", 8)).pack(anchor=tk.W)
        self.prop_template_name_entry = tk.Entry(self.template_name_frame)
        self.prop_template_name_entry.insert(0, "custom_template")
        self.prop_template_name_entry.pack(fill=tk.X, pady=2)
        
        tk.Frame(toolbox, height=1, bg="#444").pack(fill=tk.X, pady=6)

        tk.Label(toolbox, text="Contenitori / Layouts", fg="gray", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, padx=10, pady=2)
        tk.Button(toolbox, text="+ Flow Layout", command=lambda: self.add_layout_node("Flow Layout")).pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Grid Layout", command=lambda: self.add_layout_node("Grid Layout")).pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Stack Layout", command=lambda: self.add_layout_node("Stack Layout")).pack(fill=tk.X, padx=15, pady=2)

        tk.Frame(toolbox, height=1, bg="#444").pack(fill=tk.X, pady=6)

        tk.Label(toolbox, text="Componenti Utility", fg="gray", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, padx=10, pady=2)
        tk.Button(toolbox, text="+ Scroll Container", command=lambda: self.add_layout_node("Scroll Container")).pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Draggable Container", command=lambda: self.add_layout_node("Draggable Container")).pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Collapsible Container", command=lambda: self.add_layout_node("Collapsible Container")).pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Dropdown Component", command=lambda: self.add_layout_node("Dropdown")).pack(fill=tk.X, padx=15, pady=2)

        tk.Frame(toolbox, height=1, bg="#444").pack(fill=tk.X, pady=6)

        tk.Label(toolbox, text="Componenti Base (Foglia)", fg="gray", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, padx=10, pady=2)
        tk.Button(toolbox, text="+ Bottone (button)", command=lambda: self.add_leaf_node("button", "A Button"), bg="#444", fg="white").pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Testo (label)", command=lambda: self.add_leaf_node("label", "Text Label"), bg="#444", fg="white").pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Campo Testo (text-box)", command=lambda: self.add_leaf_node("text-box", ""), bg="#444", fg="white").pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Area di Testo (text-area)", command=lambda: self.add_leaf_node("text-area", ""), bg="#444", fg="white").pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Riquadro (box)", command=lambda: self.add_leaf_node("box", ""), bg="#444", fg="white").pack(fill=tk.X, padx=15, pady=2)
        tk.Button(toolbox, text="+ Spaziatore (spacer)", command=lambda: self.add_leaf_node("spacer", ""), bg="#444", fg="white").pack(fill=tk.X, padx=15, pady=2)

    def toggle_template_name_visibility(self):
        """Mostra o nasconde l'entry del nome del template senza rompere il layout"""
        if self.prop_export_template.get():
            self.template_name_frame.pack(fill=tk.X, pady=2)
        else:
            self.template_name_frame.pack_forget()

    def create_center_viewport(self):
        view_container = tk.Frame(self.root, bg=self.bg_dark)
        view_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.target_label = tk.Label(view_container, text="Selezionato: root_flow", fg=self.accent_blue, bg=self.bg_dark, font=("Arial", 10, "bold"))
        self.target_label.pack(anchor=tk.W, pady=2)
        
        self.canvas = tk.Canvas(view_container, bg="#151515", highlightthickness=1, highlightbackground="#333")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

    def create_right_property_panel(self):
        self.prop_panel = tk.Frame(self.root, width=280, bg=self.bg_panel, bd=1, relief=tk.SOLID)
        self.prop_panel.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Label(self.prop_panel, text="Property Editor", fg=self.fg_light, bg=self.bg_panel, font=("Arial", 12, "bold")).pack(pady=10)
        
        # 1. Modulo ID (Sempre visibile all'inizio se un elemento è selezionato)
        self.id_frame = tk.Frame(self.prop_panel, bg=self.bg_panel)
        tk.Label(self.id_frame, text="Widget ID:", fg="white", bg=self.bg_panel).pack(anchor=tk.W, padx=15, pady=2)
        self.prop_id_entry = tk.Entry(self.id_frame)
        self.prop_id_entry.pack(fill=tk.X, padx=15, pady=2)

        # 2. Modulo Testo (Visibile unicamente sotto l'ID per i componenti foglia o collapsible)
        self.text_frame = tk.Frame(self.prop_panel, bg=self.bg_panel)
        tk.Label(self.text_frame, text="Contenuto Testo / Titolo:", fg="white", bg=self.bg_panel).pack(anchor=tk.W, padx=15, pady=4)
        self.prop_text_entry = tk.Entry(self.text_frame)
        self.prop_text_entry.pack(fill=tk.X, padx=15, pady=2)

        # 3. Modulo Sizing Comune (Metodo Orizzontale + Verticale unificati)
        self.sizing_frame = tk.Frame(self.prop_panel, bg=self.bg_panel)
        tk.Label(self.sizing_frame, text="Metodo Orizzontale (horizontal):", fg="gray", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, padx=15, pady=4)
        self.prop_w_method = tk.StringVar(value="content")
        tk.OptionMenu(self.sizing_frame, self.prop_w_method, "content", "fill", "fixed").pack(fill=tk.X, padx=15, pady=2)
        self.prop_w_val = tk.Entry(self.sizing_frame); self.prop_w_val.pack(fill=tk.X, padx=15, pady=2)

        tk.Label(self.sizing_frame, text="Metodo Verticale (vertical):", fg="gray", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, padx=15, pady=4)
        self.prop_h_method = tk.StringVar(value="content")
        tk.OptionMenu(self.sizing_frame, self.prop_h_method, "content", "fill", "fixed").pack(fill=tk.X, padx=15, pady=2)
        self.prop_h_val = tk.Entry(self.sizing_frame); self.prop_h_val.pack(fill=tk.X, padx=15, pady=2)

        # 4. Contenitore Padding
        self.padding_frame = tk.Frame(self.prop_panel, bg=self.bg_panel)
        tk.Label(self.padding_frame, text="Tipo di Padding (Facciale):", fg="gray", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, padx=15, pady=4)
        self.prop_padding_type = tk.StringVar(value="all")
        tk.OptionMenu(self.padding_frame, self.prop_padding_type, "all", "individual", command=self.toggle_padding_views).pack(fill=tk.X, padx=15, pady=2)
        
        self.padding_placeholder_frame = tk.Frame(self.padding_frame, bg=self.bg_panel); self.padding_placeholder_frame.pack(fill=tk.X, padx=15, pady=2)
        self.pad_all_frame = tk.Frame(self.padding_placeholder_frame, bg=self.bg_panel)
        tk.Label(self.pad_all_frame, text="Valore All:", fg="white", bg=self.bg_panel).pack(side=tk.LEFT, padx=5)
        self.prop_padding_all_entry = tk.Entry(self.pad_all_frame, width=12); self.prop_padding_all_entry.pack(side=tk.LEFT, padx=5)
        
        self.pad_indiv_frame = tk.Frame(self.padding_placeholder_frame, bg=self.bg_panel)
        tk.Label(self.pad_indiv_frame, text="T:", fg="white", bg=self.bg_panel).grid(row=0, column=0, padx=2, pady=2)
        self.prop_pad_top = tk.Entry(self.pad_indiv_frame, width=5); self.prop_pad_top.grid(row=0, column=1, padx=2, pady=2)
        tk.Label(self.pad_indiv_frame, text="B:", fg="white", bg=self.bg_panel).grid(row=0, column=2, padx=2, pady=2)
        self.prop_pad_bottom = tk.Entry(self.pad_indiv_frame, width=5); self.prop_pad_bottom.grid(row=0, column=3, padx=2, pady=2)
        tk.Label(self.pad_indiv_frame, text="L:", fg="white", bg=self.bg_panel).grid(row=1, column=0, padx=2, pady=2)
        self.prop_pad_left = tk.Entry(self.pad_indiv_frame, width=5); self.prop_pad_left.grid(row=1, column=1, padx=2, pady=2)
        tk.Label(self.pad_indiv_frame, text="R:", fg="white", bg=self.bg_panel).grid(row=1, column=2, padx=2, pady=2)
        self.prop_pad_right = tk.Entry(self.pad_indiv_frame, width=5); self.prop_pad_right.grid(row=1, column=3, padx=2, pady=2)

        # 5. Contenitore Margins
        self.margins_frame = tk.Frame(self.prop_panel, bg=self.bg_panel)
        tk.Label(self.margins_frame, text="Tipo di Margini (Facciale):", fg="gray", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, padx=15, pady=4)
        self.prop_margins_type = tk.StringVar(value="all")
        tk.OptionMenu(self.margins_frame, self.prop_margins_type, "all", "individual", command=self.toggle_margins_views).pack(fill=tk.X, padx=15, pady=2)
        
        self.margins_placeholder_frame = tk.Frame(self.margins_frame, bg=self.bg_panel); self.margins_placeholder_frame.pack(fill=tk.X, padx=15, pady=2)
        self.margin_all_frame = tk.Frame(self.margins_placeholder_frame, bg=self.bg_panel)
        tk.Label(self.margin_all_frame, text="Valore All:", fg="white", bg=self.bg_panel).pack(side=tk.LEFT, padx=5)
        self.prop_margins_all_entry = tk.Entry(self.margin_all_frame, width=12); self.prop_margins_all_entry.pack(side=tk.LEFT, padx=5)
        
        self.margin_indiv_frame = tk.Frame(self.margins_placeholder_frame, bg=self.bg_panel)
        tk.Label(self.margin_indiv_frame, text="T:", fg="white", bg=self.bg_panel).grid(row=0, column=0, padx=2, pady=2)
        self.prop_margin_top = tk.Entry(self.margin_indiv_frame, width=5); self.prop_margin_top.grid(row=0, column=1, padx=2, pady=2)
        tk.Label(self.margin_indiv_frame, text="B:", fg="white", bg=self.bg_panel).grid(row=0, column=2, padx=2, pady=2)
        self.prop_margin_bottom = tk.Entry(self.margin_indiv_frame, width=5); self.prop_margin_bottom.grid(row=0, column=3, padx=2, pady=2)
        tk.Label(self.margin_indiv_frame, text="L:", fg="white", bg=self.bg_panel).grid(row=1, column=0, padx=2, pady=2)
        self.prop_margin_left = tk.Entry(self.margin_indiv_frame, width=5); self.prop_margin_left.grid(row=1, column=1, padx=2, pady=2)
        tk.Label(self.margin_indiv_frame, text="R:", fg="white", bg=self.bg_panel).grid(row=1, column=2, padx=2, pady=2)
        self.prop_margin_right = tk.Entry(self.margin_indiv_frame, width=5); self.prop_margin_right.grid(row=1, column=3, padx=2, pady=2)

        # 6. Controlli Specifici Layout
        self.layout_extra_frame = tk.Frame(self.prop_panel, bg=self.bg_panel)
        
        tk.Label(self.layout_extra_frame, text="Tipo Layout:", fg="white", bg=self.bg_panel, font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=2)
        self.prop_l_type = tk.StringVar(value="Flow Layout")
        self.prop_l_type_menu = tk.OptionMenu(
            self.layout_extra_frame, self.prop_l_type,
            "Flow Layout", "Grid Layout", "Stack Layout", "Scroll Container", "Draggable Container", "Collapsible Container", "Dropdown",
            command=self.on_layout_type_change
        )
        self.prop_l_type_menu.pack(fill=tk.X, pady=2)

        tk.Label(self.layout_extra_frame, text="Allineamento Orizzontale:", fg="white", bg=self.bg_panel).pack(anchor=tk.W, pady=2)
        self.prop_l_horiz = tk.StringVar(value="center")
        tk.OptionMenu(self.layout_extra_frame, self.prop_l_horiz, "center", "left", "right").pack(fill=tk.X)
        
        tk.Label(self.layout_extra_frame, text="Allineamento Verticale:", fg="white", bg=self.bg_panel).pack(anchor=tk.W, pady=2)
        self.prop_l_vert = tk.StringVar(value="center")
        tk.OptionMenu(self.layout_extra_frame, self.prop_l_vert, "center", "top", "bottom").pack(fill=tk.X)

        tk.Label(self.layout_extra_frame, text="Tipo Superficie (Surface):", fg="white", bg=self.bg_panel).pack(anchor=tk.W, pady=2)
        self.prop_l_surface = tk.StringVar(value="panel-dark")
        tk.OptionMenu(self.layout_extra_frame, self.prop_l_surface, "panel-dark", "vanilla-translucent", "flat-black", "none").pack(fill=tk.X)

        self.flow_prop_frame = tk.Frame(self.layout_extra_frame, bg=self.bg_panel)
        tk.Label(self.flow_prop_frame, text="Direzione Flow (direction):", fg="#2196F3", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, pady=2)
        self.prop_l_direction = tk.StringVar(value="vertical")
        tk.OptionMenu(self.flow_prop_frame, self.prop_l_direction, "vertical", "horizontal").pack(fill=tk.X)

        self.grid_prop_frame = tk.Frame(self.layout_extra_frame, bg=self.bg_panel)
        tk.Label(self.grid_prop_frame, text="R:", fg="white", bg=self.bg_panel).pack(side=tk.LEFT)
        self.prop_rows_entry = tk.Entry(self.grid_prop_frame, width=4); self.prop_rows_entry.pack(side=tk.LEFT, padx=4)
        tk.Label(self.grid_prop_frame, text="C:", fg="white", bg=self.bg_panel).pack(side=tk.LEFT)
        self.prop_cols_entry = tk.Entry(self.grid_prop_frame, width=4); self.prop_cols_entry.pack(side=tk.LEFT, padx=4)

        self.collapsible_prop_frame = tk.Frame(self.layout_extra_frame, bg=self.bg_panel)
        tk.Label(self.collapsible_prop_frame, text="Espanso di default (expanded):", fg="#E91E63", bg=self.bg_panel, font=("Arial", 8, "bold")).pack(anchor=tk.W, pady=2)
        self.prop_l_expanded = tk.StringVar(value="true")
        tk.OptionMenu(self.collapsible_prop_frame, self.prop_l_expanded, "true", "false").pack(fill=tk.X)

        # 7. Controlli Specifici Foglie
        self.leaf_extra_frame = tk.Frame(self.prop_panel, bg=self.bg_panel)
        self.label_shadow_label = tk.Label(self.leaf_extra_frame, text="Ombra Testo (Label shadow):", fg="white", bg=self.bg_panel)
        self.prop_l_shadow = tk.StringVar(value="false")
        self.label_shadow_menu = tk.OptionMenu(self.leaf_extra_frame, self.prop_l_shadow, "true", "false")
        self.label_mw_label = tk.Label(self.leaf_extra_frame, text="Larghezza Max Testo (Max-Width):", fg="white", bg=self.bg_panel)
        self.prop_l_mw = tk.Entry(self.leaf_extra_frame)

        self.text_box_max_length_label = tk.Label(self.leaf_extra_frame, text="Lunghezza Max Input (max-length):", fg="white", bg=self.bg_panel)
        self.prop_tb_max_length = tk.Entry(self.leaf_extra_frame)

        # text-area widgets
        self.text_area_max_length_label = tk.Label(self.leaf_extra_frame, text="Lunghezza Max (max-length):", fg="white", bg=self.bg_panel)
        self.prop_ta_max_length = tk.Entry(self.leaf_extra_frame)
        self.text_area_max_lines_label = tk.Label(self.leaf_extra_frame, text="Righe Max (max-lines):", fg="white", bg=self.bg_panel)
        self.prop_ta_max_lines = tk.Entry(self.leaf_extra_frame)
        self.text_area_display_count_label = tk.Label(self.leaf_extra_frame, text="Mostra Contatore (display-char-count):", fg="white", bg=self.bg_panel)
        self.prop_ta_display_count = tk.StringVar(value="false")
        self.text_area_display_count_menu = tk.OptionMenu(self.leaf_extra_frame, self.prop_ta_display_count, "true", "false")

        # box widgets
        self.box_color_mode_label = tk.Label(self.leaf_extra_frame, text="Modalità Colore:", fg="white", bg=self.bg_panel)
        self.prop_box_color_mode = tk.StringVar(value="single")
        self.box_color_mode_menu = tk.OptionMenu(self.leaf_extra_frame, self.prop_box_color_mode, "single", "gradient", command=self.toggle_box_color_mode)
        self.box_color_label = tk.Label(self.leaf_extra_frame, text="Colore (hex #AARRGGBB):", fg="white", bg=self.bg_panel)
        self.prop_box_color = tk.Entry(self.leaf_extra_frame)
        self.box_start_color_label = tk.Label(self.leaf_extra_frame, text="Colore Inizio:", fg="white", bg=self.bg_panel)
        self.prop_box_start_color = tk.Entry(self.leaf_extra_frame)
        self.box_end_color_label = tk.Label(self.leaf_extra_frame, text="Colore Fine:", fg="white", bg=self.bg_panel)
        self.prop_box_end_color = tk.Entry(self.leaf_extra_frame)
        self.box_fill_label = tk.Label(self.leaf_extra_frame, text="Riempi (fill):", fg="white", bg=self.bg_panel)
        self.prop_box_fill = tk.StringVar(value="false")
        self.box_fill_menu = tk.OptionMenu(self.leaf_extra_frame, self.prop_box_fill, "true", "false")
        self.box_direction_label = tk.Label(self.leaf_extra_frame, text="Direzione Gradiente (direction):", fg="white", bg=self.bg_panel)
        self.prop_box_direction = tk.StringVar(value="top-to-bottom")
        self.box_direction_menu = tk.OptionMenu(self.leaf_extra_frame, self.prop_box_direction, "top-to-bottom", "left-to-right", "right-to-left", "bottom-to-top")

        # spacer widgets
        self.spacer_percent_label = tk.Label(self.leaf_extra_frame, text="Percentuale (percent):", fg="white", bg=self.bg_panel)
        self.prop_spacer_percent = tk.Entry(self.leaf_extra_frame)

        # 8. Bottoni d'Azione (Sempre visibili fissati in basso)
        self.actions_frame = tk.Frame(self.prop_panel, bg=self.bg_panel)
        self.actions_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        tk.Button(self.actions_frame, text="✔️ Applica Proprietà", bg=self.accent_blue, fg="white", command=self.apply_properties).pack(fill=tk.X, padx=15, pady=5)
        tk.Button(self.actions_frame, text="❌ Elimina Componente", bg="#D32F2F", fg="white", command=self.delete_selected_component).pack(fill=tk.X, padx=15, pady=2)
        
        self.hide_property_editor()

    def toggle_padding_views(self, val):
        if val == "all":
            self.pad_indiv_frame.pack_forget()
            self.pad_all_frame.pack(fill=tk.X, pady=2)
        else:
            self.pad_all_frame.pack_forget()
            self.pad_indiv_frame.pack(fill=tk.X, pady=2)

    def toggle_margins_views(self, val):
        if val == "all":
            self.margin_indiv_frame.pack_forget()
            self.margin_all_frame.pack(fill=tk.X, pady=2)
        else:
            self.margin_all_frame.pack_forget()
            self.margin_indiv_frame.pack(fill=tk.X, pady=2)

    def _hide_leaf_extras_except(self, keep):
        if "label" not in keep:
            self.label_shadow_label.pack_forget(); self.label_shadow_menu.pack_forget()
            self.label_mw_label.pack_forget(); self.prop_l_mw.pack_forget()
        if "text-box" not in keep:
            self.text_box_max_length_label.pack_forget(); self.prop_tb_max_length.pack_forget()
        if "text-area" not in keep:
            self.text_area_max_length_label.pack_forget(); self.prop_ta_max_length.pack_forget()
            self.text_area_max_lines_label.pack_forget(); self.prop_ta_max_lines.pack_forget()
            self.text_area_display_count_label.pack_forget(); self.text_area_display_count_menu.pack_forget()
        if "box" not in keep:
            self.box_color_mode_label.pack_forget(); self.box_color_mode_menu.pack_forget()
            self.box_color_label.pack_forget(); self.prop_box_color.pack_forget()
            self.box_start_color_label.pack_forget(); self.prop_box_start_color.pack_forget()
            self.box_end_color_label.pack_forget(); self.prop_box_end_color.pack_forget()
            self.box_fill_label.pack_forget(); self.box_fill_menu.pack_forget()
            self.box_direction_label.pack_forget(); self.box_direction_menu.pack_forget()
        if "spacer" not in keep:
            self.spacer_percent_label.pack_forget(); self.prop_spacer_percent.pack_forget()

    def toggle_box_color_mode(self, val):
        if val == "single":
            self.box_start_color_label.pack_forget(); self.prop_box_start_color.pack_forget()
            self.box_end_color_label.pack_forget(); self.prop_box_end_color.pack_forget()
            self.box_direction_label.pack_forget(); self.box_direction_menu.pack_forget()
            self.box_color_label.pack(anchor=tk.W); self.prop_box_color.pack(fill=tk.X)
        else:
            self.box_color_label.pack_forget(); self.prop_box_color.pack_forget()
            self.box_start_color_label.pack(anchor=tk.W); self.prop_box_start_color.pack(fill=tk.X)
            self.box_end_color_label.pack(anchor=tk.W); self.prop_box_end_color.pack(fill=tk.X)
            self.box_direction_label.pack(anchor=tk.W); self.box_direction_menu.pack(fill=tk.X)

    def on_layout_type_change(self, val):
        """Nasconde o mostra dinamicamente i campi specifici quando si cambia tipo di layout"""
        if self.selected_component and isinstance(self.selected_component, UILayout):
            self.selected_component.layout_type = val
            self.show_property_editor(self.selected_component)

    # =====================================================================
    # MOTORE GERARCHICO DI CALCOLO DELLE BOUNDS (AUTO-SNAPPING)
    # =====================================================================

    def rebuild_and_snap(self):
        self.canvas.delete("all")
        cx1, cy1, cx2, cy2 = 40, 40, 680, 560
        
        # Evidenzia in blu il bordo del root se selezionato, altrimenti grigio scuro
        root_color = self.accent_blue if self.selected_component == self.main_layout else "#444"
        self.canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="#1a1a1a", outline=root_color, width=2, tags=f"click_{self.main_layout.id}")
        self.canvas.create_text(cx1+10, cy1+15, text="Game Viewport (oωo Layout Snapping)", fill="gray", anchor=tk.W, tags=f"click_{self.main_layout.id}")
        
        self.main_layout.bounds = (cx1, cy1, cx2, cy2)
        self.render_layout_recursive(self.main_layout, cx1+20, cy1+40, cx2-20, cy2-20)
        
        if self.selected_component:
            display_name = self.selected_component.id
            if isinstance(self.selected_component, UILayout):
                if self.selected_component.layout_type in ["Flow Layout", "Scroll Container", "Collapsible Container"]:
                    display_type = f"{self.selected_component.layout_type} ({self.selected_component.direction})"
                else:
                    display_type = self.selected_component.layout_type
            else:
                display_type = self.selected_component.type
            self.target_label.config(text=f"Selezionato: {display_name} ({display_type})", fg=self.accent_blue)

    def render_layout_recursive(self, layout, x1, y1, x2, y2):
        is_root = (layout.id == "root_flow")
        
        colors_map = {
            "Flow Layout": "#FF9800",
            "Grid Layout": "#9C27B0",
            "Stack Layout": "#FF5722",
            "Scroll Container": "#00BCD4",
            "Draggable Container": "#4CAF50",
            "Collapsible Container": "#E91E63",
            "Dropdown": "#607D8B"
        }
        color = colors_map.get(layout.layout_type, "#FF9800")
        if self.selected_component == layout and not is_root: color = self.accent_blue
        
        if not is_root:
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, dash=(3, 3), tags=f"click_{layout.id}")
            display_info = f"{layout.id} [{layout.layout_type}]"
            if layout.layout_type in ["Flow Layout", "Scroll Container", "Collapsible Container", "Stack Layout"]:
                display_info += f" ({layout.direction})"
            self.canvas.create_text(x1+5, y1+10, text=display_info, fill=color, font=("Arial", 8, "bold"), anchor=tk.W)
            
        layout.bounds = (int(x1), int(y1), int(x2), int(y2))
        if not layout.children: return

        num_children = len(layout.children)
        for i, child in enumerate(layout.children):
            cx1, cy1, cx2, cy2 = x1, y1, x2, y2

            if layout.layout_type in ["Flow Layout", "Scroll Container", "Collapsible Container"] and layout.direction == "vertical":
                slot_h = (y2 - y1) / num_children
                cx1, cy1 = x1 + 10, y1 + (i * slot_h) + 12
                cx2, cy2 = x2 - 10, y1 + ((i + 1) * slot_h) - 8
            elif layout.layout_type in ["Flow Layout", "Scroll Container", "Collapsible Container"] and layout.direction == "horizontal":
                slot_w = (x2 - x1) / num_children
                cx1, cy1 = x1 + (i * slot_w) + 10, y1 + 12
                cx2, cy2 = x1 + ((i + 1) * slot_w) - 10, y2 - 8
            else: 
                slot_h = (y2 - y1) / num_children
                cx1, cy1 = x1 + 10, y1 + (i * slot_h) + 12
                cx2, cy2 = x2 - 10, y1 + ((i + 1) * slot_h) - 8

            if layout.layout_type == "Grid Layout":
                try:
                    r_max, c_max = max(1, int(layout.rows)), max(1, int(layout.cols))
                except ValueError:
                    r_max, c_max = 2, 2
                r, c = i // c_max, i % c_max
                slot_w, slot_h = (x2 - x1) / c_max, (y2 - y1) / r_max
                cx1, cy1 = x1 + (c * slot_w) + 6, y1 + (r * slot_h) + 12
                cx2, cy2 = x1 + ((c + 1) * slot_w) - 6, y1 + ((r + 1) * slot_h) - 6

            child.bounds = (int(cx1), int(cy1), int(cx2), int(cy2))

            if isinstance(child, UILayout):
                self.render_layout_recursive(child, cx1, cy1, cx2, cy2)
            elif isinstance(child, UIComponent):
                colors = {"button": "#3a3a3a", "label": "#151515", "text-box": "#1a2a3a", "text-area": "#1a2a1a", "box": "#2a1a1a", "spacer": "#252525"}
                outlines = {"button": "#fff", "label": "#555", "text-box": "#4FC3F7", "text-area": "#81C784", "box": "#FF7043", "spacer": "#888"}
                
                b_color = colors.get(child.type, "#3a3a3a") if self.selected_component != child else "#555"
                o_color = outlines.get(child.type, "#fff") if self.selected_component != child else self.accent_blue
                
                self.canvas.create_rectangle(cx1, cy1, cx2, cy2, fill=b_color, outline=o_color, width=1.5, tags=f"click_{child.id}")
                text_disp = f"[{child.type}] {child.text}"
                self.canvas.create_text((cx1+cx2)/2, (cy1+cy2)/2, text=text_disp, fill="white", font=("Arial", 9), tags=f"click_{child.id}")

    # =====================================================================
    # SEPARAZIONE NETTA TRA CLICK DI SELEZIONE E TRASCINAMENTO
    # =====================================================================

    def on_canvas_click(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.is_dragging = False
        self.dragged_component = None

        clicked_tags = self.canvas.find_withtag(tk.CURRENT)
        if not clicked_tags:
            self.selected_component = self.main_layout
            self.show_property_editor(self.main_layout)
            self.rebuild_and_snap()
            return
            
        for tag in self.canvas.gettags(clicked_tags[0]):
            if tag.startswith("click_"):
                comp_id = tag.replace("click_", "")
                comp = self.find_component_by_id(self.main_layout, comp_id)
                if comp:
                    self.selected_component = comp
                    self.show_property_editor(comp)
                    self.rebuild_and_snap()
                    return

    def on_canvas_drag(self, event):
        if not self.selected_component or self.selected_component.id == "root_flow": return
        dx = abs(event.x - self.start_x)
        dy = abs(event.y - self.start_y)
        
        if not self.is_dragging and (dx > 5 or dy > 5):
            self.is_dragging = True
            self.dragged_component = self.selected_component
                
        if self.is_dragging:
            if self.drag_proxy: self.canvas.delete(self.drag_proxy)
            self.drag_proxy = self.canvas.create_rectangle(event.x - 50, event.y - 15, event.x + 50, event.y + 15, outline="#2196F3", width=2, fill="#2196F3", stipple="gray25")

    def on_canvas_release(self, event):
        if self.drag_proxy: self.canvas.delete(self.drag_proxy); self.drag_proxy = None
        if self.is_dragging and self.dragged_component:
            target_layout = self.find_layout_at_coords(self.main_layout, event.x, event.y)
            if target_layout and target_layout != self.dragged_component and not self.is_child_of(target_layout, self.dragged_component):
                target_layout.add_child(self.dragged_component)
                self.selected_component = self.dragged_component
                self.show_property_editor(self.dragged_component)
        self.dragged_component = None
        self.is_dragging = False
        self.rebuild_and_snap()

    def find_layout_at_coords(self, current_layout, x, y):
        bx1, by1, bx2, by2 = current_layout.bounds
        if not (bx1 <= x <= bx2 and by1 <= y <= by2): return None
        for child in current_layout.children:
            if isinstance(child, UILayout):
                found = self.find_layout_at_coords(child, x, y)
                if found: return found
        return current_layout

    def is_child_of(self, node, potential_parent):
        current = node.parent
        while current:
            if current == potential_parent: return True
            current = current.parent
        return False

    def find_component_by_id(self, current_node, target_id):
        if current_node.id == target_id: return current_node
        if isinstance(current_node, UILayout):
            for child in current_node.children:
                found = self.find_component_by_id(child, target_id)
                if found: return found
        return None

    def get_active_layout_parent(self):
        if isinstance(self.selected_component, UILayout):
            return self.selected_component
        elif self.selected_component and self.selected_component.parent:
            return self.selected_component.parent
        return self.main_layout

    def add_layout_node(self, layout_type):
        parent = self.get_active_layout_parent()
        l_id = f"layout_{self.layout_counter}"
        self.layout_counter += 1
        new_layout = UILayout(l_id, layout_type)
        if parent.add_child(new_layout):
            self.selected_component = new_layout
            self.rebuild_and_snap()
            self.show_property_editor(new_layout)

    def add_leaf_node(self, leaf_type, default_text):
        parent = self.get_active_layout_parent()
        w_id = f"{leaf_type}_{self.widget_counter}"
        self.widget_counter += 1
        new_node = UIComponent(w_id, comp_type=leaf_type, text=default_text)
        if parent.add_child(new_node):
            self.selected_component = new_node
            self.rebuild_and_snap()
            self.show_property_editor(new_node)

    def remove_component_recursive(self, current_layout, target_node):
        if target_node in current_layout.children:
            current_layout.remove_child(target_node)
            return True
        for child in current_layout.children:
            if isinstance(child, UILayout):
                if self.remove_component_recursive(child, target_node): return True
        return False

    def delete_selected_component(self):
        if not self.selected_component or self.selected_component.id == "root_flow": return
        if self.remove_component_recursive(self.main_layout, self.selected_component):
            self.selected_component = self.main_layout
            self.show_property_editor(self.main_layout)
            self.rebuild_and_snap()

    # =====================================================================
    # PROPERTY EDITOR STRUTTURATO (ID E TESTO IN CIMA CORRETTI)
    # =====================================================================

    def show_property_editor(self, comp):
        # 1. Reset e smontaggio completo di tutti i moduli visivi
        self.hide_property_editor()

        # 2. Montiamo l'id_frame ad albero per PRIMO (Sempre visibile per Layout e foglie!)
        self.id_frame.pack(fill=tk.X)
        self.prop_id_entry.delete(0, tk.END); self.prop_id_entry.insert(0, comp.id)

        # Mostra testo solo per foglie che lo supportano, o per Collapsible Container
        if (isinstance(comp, UILayout) and comp.layout_type == "Collapsible Container") or \
           (not isinstance(comp, UILayout) and comp.type not in ["spacer", "box"]):
            self.text_frame.pack(fill=tk.X)
            self.prop_text_entry.delete(0, tk.END); self.prop_text_entry.insert(0, comp.text)

        # 3. Attiviamo i blocchi comuni geometrici standard (Sizing compattato, Padding e Margini)
        self.sizing_frame.pack(fill=tk.X)
        self.padding_frame.pack(fill=tk.X)
        self.margins_frame.pack(fill=tk.X)

        if isinstance(comp, UILayout):
            # Se è un layout monta le opzioni di allineamento e superficie extra
            self.layout_extra_frame.pack(fill=tk.X, padx=15, pady=5)
            
            self.prop_l_type.set(comp.layout_type)
            self.prop_l_horiz.set(comp.horiz_align)
            self.prop_l_vert.set(comp.vert_align)
            self.prop_l_surface.set(comp.surface_type)
            
            self.prop_l_direction.set(comp.direction)
            self.prop_l_expanded.set(comp.expanded)
            
            self.prop_rows_entry.delete(0, tk.END); self.prop_rows_entry.insert(0, comp.rows)
            self.prop_cols_entry.delete(0, tk.END); self.prop_cols_entry.insert(0, comp.cols)
            
            # Svuota i moduli specifici prima di iniettare quelli coerenti al tipo selezionato
            self.flow_prop_frame.pack_forget()
            self.grid_prop_frame.pack_forget()
            self.collapsible_prop_frame.pack_forget()
            
            if comp.layout_type in ["Flow Layout", "Scroll Container", "Collapsible Container"]:
                self.flow_prop_frame.pack(fill=tk.X, pady=4)
            if comp.layout_type == "Grid Layout":
                self.grid_prop_frame.pack(fill=tk.X, pady=4)
            if comp.layout_type == "Collapsible Container":
                self.collapsible_prop_frame.pack(fill=tk.X, pady=4)
        else:
            # Per le foglie, attiva il modulo opzioni avanzate del widget
            self.leaf_extra_frame.pack(fill=tk.X, padx=15, pady=5)
            
            if comp.type == "label":
                self._hide_leaf_extras_except(["label"])
                self.label_shadow_label.pack(anchor=tk.W); self.label_shadow_menu.pack(fill=tk.X)
                self.label_mw_label.pack(anchor=tk.W); self.prop_l_mw.pack(fill=tk.X)
                self.prop_l_shadow.set(comp.label_shadow)
                self.prop_l_mw.delete(0, tk.END); self.prop_l_mw.insert(0, comp.label_max_width)
            elif comp.type == "text-box":
                self.label_shadow_label.pack_forget(); self.label_shadow_menu.pack_forget()
                self.label_mw_label.pack_forget(); self.prop_l_mw.pack_forget()
                self.text_box_max_length_label.pack(anchor=tk.W); self.prop_tb_max_length.pack(fill=tk.X)
                self.prop_tb_max_length.delete(0, tk.END); self.prop_tb_max_length.insert(0, comp.text_box_max_length)
                self._hide_leaf_extras_except(["text-box"])
            elif comp.type == "text-area":
                self._hide_leaf_extras_except(["text-area"])
                self.text_area_max_length_label.pack(anchor=tk.W); self.prop_ta_max_length.pack(fill=tk.X)
                self.text_area_max_lines_label.pack(anchor=tk.W); self.prop_ta_max_lines.pack(fill=tk.X)
                self.text_area_display_count_label.pack(anchor=tk.W); self.text_area_display_count_menu.pack(fill=tk.X)
                self.prop_ta_max_length.delete(0, tk.END); self.prop_ta_max_length.insert(0, comp.text_area_max_length)
                self.prop_ta_max_lines.delete(0, tk.END); self.prop_ta_max_lines.insert(0, comp.text_area_max_lines)
                self.prop_ta_display_count.set(comp.text_area_display_char_count)
            elif comp.type == "box":
                self._hide_leaf_extras_except(["box"])
                self.box_color_mode_label.pack(anchor=tk.W); self.box_color_mode_menu.pack(fill=tk.X)
                self.prop_box_color_mode.set(comp.box_color_mode)
                self.box_fill_label.pack(anchor=tk.W); self.box_fill_menu.pack(fill=tk.X)
                self.prop_box_fill.set(comp.box_fill)
                self.toggle_box_color_mode(comp.box_color_mode)
                self.prop_box_color.delete(0, tk.END); self.prop_box_color.insert(0, comp.box_color)
                self.prop_box_start_color.delete(0, tk.END); self.prop_box_start_color.insert(0, comp.box_start_color)
                self.prop_box_end_color.delete(0, tk.END); self.prop_box_end_color.insert(0, comp.box_end_color)
                self.prop_box_direction.set(comp.box_direction)
            elif comp.type == "spacer":
                self._hide_leaf_extras_except(["spacer"])
                self.spacer_percent_label.pack(anchor=tk.W); self.prop_spacer_percent.pack(fill=tk.X)
                self.prop_spacer_percent.delete(0, tk.END); self.prop_spacer_percent.insert(0, comp.spacer_percent)
            else:
                self._hide_leaf_extras_except([])

        # 4. Sincronizzazione delle variabili geometriche con i dati correnti del modello
        self.prop_w_method.set(comp.width_method)
        self.prop_w_val.delete(0, tk.END); self.prop_w_val.insert(0, comp.width_value)
        self.prop_h_method.set(comp.height_method)
        self.prop_h_val.delete(0, tk.END); self.prop_h_val.insert(0, comp.height_value)
        
        self.prop_padding_type.set(comp.padding_type)
        self.prop_padding_all_entry.delete(0, tk.END); self.prop_padding_all_entry.insert(0, comp.padding_all)
        self.prop_pad_top.delete(0, tk.END); self.prop_pad_top.insert(0, comp.padding_top)
        self.prop_pad_bottom.delete(0, tk.END); self.prop_pad_bottom.insert(0, comp.padding_bottom)
        self.prop_pad_left.delete(0, tk.END); self.prop_pad_left.insert(0, comp.padding_left)
        self.prop_pad_right.delete(0, tk.END); self.prop_pad_right.insert(0, comp.padding_right)
        self.toggle_padding_views(comp.padding_type)
        
        self.prop_margins_type.set(comp.margins_type)
        self.prop_margins_all_entry.delete(0, tk.END); self.prop_margins_all_entry.insert(0, comp.margins_all)
        self.prop_margin_top.delete(0, tk.END); self.prop_margin_top.insert(0, comp.margins_top)
        self.prop_margin_bottom.delete(0, tk.END); self.prop_margin_bottom.insert(0, comp.margins_bottom)
        self.prop_margin_left.delete(0, tk.END); self.prop_margin_left.insert(0, comp.margins_left)
        self.prop_margin_right.delete(0, tk.END); self.prop_margin_right.insert(0, comp.margins_right)
        self.toggle_margins_views(comp.margins_type)

    def hide_property_editor(self):
        """Smonta in blocco e pulisce l'intero pannello quando non c'è selezione attiva"""
        self.id_frame.pack_forget()
        self.text_frame.pack_forget()
        self.sizing_frame.pack_forget()
        self.padding_frame.pack_forget()
        self.margins_frame.pack_forget()
        self.layout_extra_frame.pack_forget()
        self.leaf_extra_frame.pack_forget()

    def apply_properties(self):
        if not self.selected_component: return
        
        # Validazione e applicazione dell'ID valida estesa per TUTTI gli elementi (Layout inclusi)
        new_id = self.prop_id_entry.get().strip().replace(" ", "_")
        if not new_id: return
        if new_id != self.selected_component.id and self.find_component_by_id(self.main_layout, new_id) is not None:
            messagebox.showerror("Errore ID", "ID già esistente!")
            return
        self.selected_component.id = new_id
        
        if not isinstance(self.selected_component, UILayout) and self.selected_component.type not in ["spacer", "box"]:
            self.selected_component.text = self.prop_text_entry.get()
            
        self.selected_component.width_method = self.prop_w_method.get()
        self.selected_component.width_value = self.prop_w_val.get()
        self.selected_component.height_method = self.prop_h_method.get()
        self.selected_component.height_value = self.prop_h_val.get()
        
        self.selected_component.padding_type = self.prop_padding_type.get()
        self.selected_component.padding_all = self.prop_padding_all_entry.get()
        self.selected_component.padding_top = self.prop_pad_top.get()
        self.selected_component.padding_bottom = self.prop_pad_bottom.get()
        self.selected_component.padding_left = self.prop_pad_left.get()
        self.selected_component.padding_right = self.prop_pad_right.get()
        
        self.selected_component.margins_type = self.prop_margins_type.get()
        self.selected_component.margins_all = self.prop_margins_all_entry.get()
        self.selected_component.margins_top = self.prop_margin_top.get()
        self.selected_component.margins_bottom = self.prop_margin_bottom.get()
        self.selected_component.margins_left = self.prop_margin_left.get()
        self.selected_component.margins_right = self.prop_margin_right.get()
        
        if isinstance(self.selected_component, UILayout):
            self.selected_component.layout_type = self.prop_l_type.get()
            self.selected_component.horiz_align = self.prop_l_horiz.get()
            self.selected_component.vert_align = self.prop_l_vert.get()
            self.selected_component.surface_type = self.prop_l_surface.get()
            
            if self.selected_component.layout_type in ["Flow Layout", "Scroll Container", "Collapsible Container"]:
                self.selected_component.direction = self.prop_l_direction.get()
            if self.selected_component.layout_type == "Grid Layout":
                self.selected_component.rows = self.prop_rows_entry.get()
                self.selected_component.cols = self.prop_cols_entry.get()
            if self.selected_component.layout_type == "Collapsible Container":
                self.selected_component.expanded = self.prop_l_expanded.get()
                self.selected_component.text = self.prop_text_entry.get() 
        else:
            if self.selected_component.type == "label":
                self.selected_component.label_shadow = self.prop_l_shadow.get()
                self.selected_component.label_max_width = self.prop_l_mw.get()
            elif self.selected_component.type == "text-box":
                self.selected_component.text_box_max_length = self.prop_tb_max_length.get()
            elif self.selected_component.type == "text-area":
                self.selected_component.text_area_max_length = self.prop_ta_max_length.get()
                self.selected_component.text_area_max_lines = self.prop_ta_max_lines.get()
                self.selected_component.text_area_display_char_count = self.prop_ta_display_count.get()
            elif self.selected_component.type == "box":
                self.selected_component.box_color_mode = self.prop_box_color_mode.get()
                self.selected_component.box_color = self.prop_box_color.get()
                self.selected_component.box_start_color = self.prop_box_start_color.get()
                self.selected_component.box_end_color = self.prop_box_end_color.get()
                self.selected_component.box_fill = self.prop_box_fill.get()
                self.selected_component.box_direction = self.prop_box_direction.get()
            elif self.selected_component.type == "spacer":
                self.selected_component.spacer_percent = self.prop_spacer_percent.get()
                
        self.rebuild_and_snap()

# =====================================================================
# SEZIONE EXPORT XML / IMPORT XML VALIDATO AD ALBERO XSD
# =====================================================================

    def export_xml(self):
        owo_ui = ET.Element("owo-ui", {
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:noNamespaceSchemaLocation": "https://raw.githubusercontent.com/wisp-forest/owo-lib/1.20/owo-ui.xsd"
        })
        
        if self.prop_export_template.get():
            templates_node = ET.SubElement(owo_ui, "templates")
            template_name = self.prop_template_name_entry.get().strip().replace(" ", "_")
            if not template_name:
                template_name = "custom_template"
            template_node = ET.SubElement(templates_node, "template", {"name": template_name})
            self.serialize_node_recursive(template_node, self.main_layout)
        else:
            components_node = ET.SubElement(owo_ui, "components")
            self.serialize_node_recursive(components_node, self.main_layout)
        
        xml_str = ET.tostring(owo_ui, encoding="utf-8")
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="    ")
        
        # Persistenza nome file: Pre-compilazione dati geometrici originari
        initial_name = os.path.basename(self.current_file_path) if self.current_file_path else "nuovo_layout.xml"
        initial_dir = os.path.dirname(self.current_file_path) if self.current_file_path else "."

        file_path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=initial_name,
            defaultextension=".xml", 
            filetypes=[("XML Files", "*.xml")]
        )
        if file_path:
            self.current_file_path = file_path
            with open(file_path, "w", encoding="utf-8") as f: f.write(pretty_xml)
            messagebox.showinfo("Successo", "XML valido al 100% esportato seguendo le specifiche del file XSD!")

    def serialize_node_recursive(self, xml_parent, obj, grid_pos=None):
        attrs = {"id": obj.id}
        if grid_pos is not None:
            attrs["row"] = str(grid_pos[0])
            attrs["column"] = str(grid_pos[1]) 
        if isinstance(obj, UILayout):
            if obj.layout_type == "Flow Layout":
                tag = "flow-layout"
                attrs["direction"] = obj.direction
            elif obj.layout_type == "Grid Layout":
                tag = "grid-layout"
                attrs["rows"] = obj.rows
                attrs["columns"] = obj.cols
            elif obj.layout_type == "Scroll Container":
                tag = "scroll"
                attrs["direction"] = obj.direction
            elif obj.layout_type == "Draggable Container":
                tag = "drag"
            elif obj.layout_type == "Collapsible Container":
                tag = "collapsible"
                attrs["direction"] = obj.direction
                attrs["expanded"] = obj.expanded
            elif obj.layout_type == "Stack Layout":
                tag = "stack-layout"
            elif obj.layout_type == "Dropdown":
                tag = "dropdown"
            else:
                return
        else:
            tag = obj.type
            if tag == "spacer" and obj.spacer_percent:
                attrs["percent"] = obj.spacer_percent

        node = ET.SubElement(xml_parent, tag, attrs)
        
        if isinstance(obj, UILayout) and obj.children:
            # CORREZIONE COMPATIBILITÀ: scroll e drag NON usano il raggruppatore visivo <children>
            if obj.layout_type in ["Scroll Container", "Draggable Container"]:
                if obj.children:
                    self.serialize_node_recursive(node, obj.children[0])
            elif obj.layout_type == "Grid Layout":
                children_container = ET.SubElement(node, "children")
                try:
                    cols = max(1, int(obj.cols))
                except ValueError:
                    cols = 2
                for i, child in enumerate(obj.children):
                    self.serialize_node_recursive(children_container, child, grid_pos=(i // cols, i % cols))
            else:
                children_container = ET.SubElement(node, "children")
                for child in obj.children:
                    self.serialize_node_recursive(children_container, child)

        if tag in ["button", "label", "collapsible", "text-box"] and obj.text:
            ET.SubElement(node, "text").text = obj.text

        if tag == "text-box" and obj.text_box_max_length:
            ET.SubElement(node, "max-length").text = obj.text_box_max_length

        if tag == "text-area":
            if obj.text: ET.SubElement(node, "text").text = obj.text
            if obj.text_area_max_length: ET.SubElement(node, "max-length").text = obj.text_area_max_length
            if obj.text_area_max_lines: ET.SubElement(node, "max-lines").text = obj.text_area_max_lines
            if obj.text_area_display_char_count == "true": ET.SubElement(node, "display-char-count").text = "true"

        if tag == "box":
            if obj.box_color_mode == "single":
                if obj.box_color: ET.SubElement(node, "color").text = obj.box_color
            else:
                if obj.box_start_color: ET.SubElement(node, "start-color").text = obj.box_start_color
                if obj.box_end_color: ET.SubElement(node, "end-color").text = obj.box_end_color
                if obj.box_direction != "top-to-bottom": ET.SubElement(node, "direction").text = obj.box_direction
            if obj.box_fill == "true": ET.SubElement(node, "fill").text = "true"

        if tag == "label":
            if obj.label_shadow == "true": ET.SubElement(node, "shadow").text = "true"
            if obj.label_max_width: ET.SubElement(node, "max-width").text = obj.label_max_width

        sizing_node = ET.SubElement(node, "sizing")
        w_val = str(obj.width_value) if obj.width_method in ["fill", "fixed"] else "0"
        h_node = ET.SubElement(sizing_node, "horizontal", {"method": obj.width_method})
        h_node.text = w_val
            
        l_val = str(obj.height_value) if obj.height_method in ["fill", "fixed"] else "0"
        v_node = ET.SubElement(sizing_node, "vertical", {"method": obj.height_method})
        v_node.text = l_val

        # Compilazione tag <margins>
        has_margins = False
        if obj.margins_type == "all" and obj.margins_all != "0": has_margins = True
        elif obj.margins_type == "individual" and (obj.margins_top != "0" or obj.margins_bottom != "0" or obj.margins_left != "0" or obj.margins_right != "0"): has_margins = True
        
        if has_margins:
            margins_node = ET.SubElement(node, "margins")
            if obj.margins_type == "all":
                ET.SubElement(margins_node, "all").text = obj.margins_all
            else:
                if obj.margins_top != "0": ET.SubElement(margins_node, "top").text = str(obj.margins_top)
                if obj.margins_bottom != "0": ET.SubElement(margins_node, "bottom").text = str(obj.margins_bottom)
                if obj.margins_left != "0": ET.SubElement(margins_node, "left").text = str(obj.margins_left)
                if obj.margins_right != "0": ET.SubElement(margins_node, "right").text = str(obj.margins_right)
            
        # Compilazione tag <padding>
        has_padding = False
        if obj.padding_type == "all" and obj.padding_all != "0": has_padding = True
        elif obj.padding_type == "individual" and (obj.padding_top != "0" or obj.padding_bottom != "0" or obj.padding_left != "0" or obj.padding_right != "0"): has_padding = True
        
        if has_padding or isinstance(obj, UILayout):
            padding_node = ET.SubElement(node, "padding")
            if obj.padding_type == "all":
                ET.SubElement(padding_node, "all").text = obj.padding_all
            else:
                if obj.padding_top != "0": ET.SubElement(padding_node, "top").text = str(obj.padding_top)
                if obj.padding_bottom != "0": ET.SubElement(padding_node, "bottom").text = str(obj.padding_bottom)
                if obj.padding_left != "0": ET.SubElement(padding_node, "left").text = str(obj.padding_left)
                if obj.padding_right != "0": ET.SubElement(padding_node, "right").text = str(obj.padding_right)

        if isinstance(obj, UILayout):
            ET.SubElement(node, "horizontal-alignment").text = obj.horiz_align
            ET.SubElement(node, "vertical-alignment").text = obj.vert_align
            
            if obj.surface_type != "none":
                surface_node = ET.SubElement(node, "surface")
                if obj.surface_type == "panel-dark": ET.SubElement(surface_node, "panel", {"dark": "true"})
                elif obj.surface_type == "vanilla-translucent": ET.SubElement(surface_node, "vanilla-translucent")
                elif obj.surface_type == "flat-black": ET.SubElement(surface_node, "flat").text = "#C0101010"

    def import_xml(self):
        file_path = filedialog.askopenfilename(filetypes=[("XML Files", "*.xml")])
        if not file_path: return
        try:
            self.current_file_path = file_path

            tree = ET.parse(file_path)
            root = tree.getroot()
            
            components = root.find("components")
            main_flow = None
            is_template = False
            t_name = "custom_template"
            
            if components is not None:
                main_flow = components.find("flow-layout") or components.find("grid-layout") or components.find("scroll") or components.find("drag") or components.find("collapsible") or components.find("dropdown")
            else:
                templates = root.find("templates")
                if templates is not None:
                    template_el = templates.find("template")
                    if template_el is not None:
                        main_flow = template_el.find("flow-layout") or template_el.find("grid-layout") or template_el.find("scroll") or template_el.find("drag") or template_el.find("collapsible") or template_el.find("dropdown")
                        is_template = True
                        t_name = template_el.get("name", "custom_template")
            
            if main_flow is None:
                messagebox.showerror("Errore", "Impossibile trovare un layout radice valido (<flow-layout>, <grid-layout> o <scroll/drag/collapsible/dropdown>)")
                return
            
            self.prop_export_template.set(is_template)
            self.prop_template_name_entry.delete(0, tk.END)
            self.prop_template_name_entry.insert(0, t_name)
            self.toggle_template_name_visibility()
            
            if main_flow.tag == "grid-layout":
                l_type = "Grid Layout"
            elif main_flow.tag == "flow-layout":
                l_type = "Flow Layout"
            elif main_flow.tag == "scroll":
                l_type = "Scroll Container"
            elif main_flow.tag == "drag":
                l_type = "Draggable Container"
            elif main_flow.tag == "collapsible":
                l_type = "Collapsible Container"
            elif main_flow.tag == "dropdown":
                l_type = "Dropdown"
            else:
                l_type = "Flow Layout"
            
            l_id = main_flow.get("id")
            if not l_id:
                l_id = "root_flow"
            
            self.main_layout = UILayout(l_id, l_type, main_flow.get("rows", "2"), main_flow.get("columns", "2"), direction=main_flow.get("direction", "vertical"))
            
            if l_type == "Collapsible Container":
                self.main_layout.expanded = main_flow.get("expanded", "true")
                text_node = main_flow.find("text")
                self.main_layout.text = safe_text(text_node, "")

            p_node = main_flow.find("padding")
            if p_node is not None:
                all_node = p_node.find("all")
                if all_node is not None:
                    self.main_layout.padding_type = "all"
                    self.main_layout.padding_all = safe_text(all_node, "0")
                else:
                    self.main_layout.padding_type = "individual"
                    self.main_layout.padding_top = safe_text(p_node.find("top"), "0")
                    self.main_layout.padding_bottom = safe_text(p_node.find("bottom"), "0")
                    self.main_layout.padding_left = safe_text(p_node.find("left"), "0")
                    self.main_layout.padding_right = safe_text(p_node.find("right"), "0")

            m_node = main_flow.find("margins")
            if m_node is not None:
                all_node = m_node.find("all")
                if all_node is not None:
                    self.main_layout.margins_type = "all"
                    self.main_layout.margins_all = safe_text(all_node, "0")
                else:
                    self.main_layout.margins_type = "individual"
                    self.main_layout.margins_top = safe_text(m_node.find("top"), "0")
                    self.main_layout.margins_bottom = safe_text(m_node.find("bottom"), "0")
                    self.main_layout.margins_left = safe_text(m_node.find("left"), "0")
                    self.main_layout.margins_right = safe_text(m_node.find("right"), "0")

            sizing = main_flow.find("sizing")
            if sizing is not None:
                h_xml = sizing.find("horizontal")
                if h_xml is not None:
                    self.main_layout.width_method = h_xml.get("method", "content")
                    self.main_layout.width_value = safe_text(h_xml, "100")
                v_xml = sizing.find("vertical")
                if v_xml is not None:
                    self.main_layout.height_method = v_xml.get("method", "content")
                    self.main_layout.height_value = safe_text(v_xml, "100")

            # Carica l'allineamento orizzontale e verticale originale per il blocco root
            h_align = main_flow.find("horizontal-alignment")
            if h_align is not None: self.main_layout.horiz_align = safe_text(h_align, "center")
            v_align = main_flow.find("vertical-alignment")
            if v_align is not None: self.main_layout.vert_align = safe_text(v_align, "center")

            # Carica la superficie originale per il blocco root
            surf_node = main_flow.find("surface")
            if surf_node is not None:
                if surf_node.find("panel") is not None:
                    self.main_layout.surface_type = "panel-dark"
                elif surf_node.find("vanilla-translucent") is not None:
                    self.main_layout.surface_type = "vanilla-translucent"
                elif surf_node.find("flat") is not None:
                    self.main_layout.surface_type = "flat-black"
                else:
                    self.main_layout.surface_type = "none"
            else:
                self.main_layout.surface_type = "none"

            self.selected_component = self.main_layout
            self.show_property_editor(self.main_layout)
            
            # CORREZIONE IMPORTER ROOT: Esegue il parse selettivo ignorando i tag fittizi dei wrapping parent
            if l_type in ["Scroll Container", "Draggable Container"]:
                for sub in main_flow:
                    if sub.tag not in ["sizing", "margins", "padding", "surface", "text", "horizontal-alignment", "vertical-alignment"]:
                        self.parse_xml_recursive([sub], self.main_layout)
                        break
            else:
                main_children = main_flow.find("children")
                if main_children is not None: self.parse_xml_recursive(main_children, self.main_layout)
                
            self.rebuild_and_snap()
            messagebox.showinfo("Importato", "File XML importato correttamente!")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile parsare l'XML: {e}")

    def parse_xml_recursive(self, xml_children, parent_obj):
        for child in xml_children:
            if child.tag in ["flow-layout", "grid-layout", "stack-layout", "scroll", "drag", "collapsible", "dropdown"]:
                if child.tag == "grid-layout":
                    l_type = "Grid Layout"
                elif child.tag == "flow-layout":
                    l_type = "Flow Layout"
                elif child.tag == "scroll":
                    l_type = "Scroll Container"
                elif child.tag == "drag":
                    l_type = "Draggable Container"
                elif child.tag == "collapsible":
                    l_type = "Collapsible Container"
                elif child.tag == "stack-layout":
                    l_type = "Stack Layout"
                elif child.tag == "dropdown":
                    l_type = "Dropdown"
                else:
                    l_type = "Flow Layout"
                
                l_id = child.get("id", f"layout_{self.layout_counter}")
                if f"layout_{self.layout_counter}" == l_id:
                    self.layout_counter += 1
                
                sub_layout = UILayout(l_id, l_type, child.get("rows", "2"), child.get("columns", "2"), direction=child.get("direction", "vertical"))
                
                if l_type == "Collapsible Container":
                    sub_layout.expanded = child.get("expanded", "true")
                    text_node = child.find("text")
                    sub_layout.text = safe_text(text_node, "")

                p_node = child.find("padding")
                if p_node is not None:
                    all_node = p_node.find("all")
                    if all_node is not None:
                        sub_layout.padding_type = "all"
                        sub_layout.padding_all = safe_text(all_node, "0")
                    else:
                        sub_layout.padding_type = "individual"
                        sub_layout.padding_top = safe_text(p_node.find("top"), "0")
                        sub_layout.padding_bottom = safe_text(p_node.find("bottom"), "0")
                        sub_layout.padding_left = safe_text(p_node.find("left"), "0")
                        sub_layout.padding_right = safe_text(p_node.find("right"), "0")

                m_node = child.find("margins")
                if m_node is not None:
                    all_node = m_node.find("all")
                    if all_node is not None:
                        sub_layout.margins_type = "all"
                        sub_layout.margins_all = safe_text(all_node, "0")
                    else:
                        sub_layout.margins_type = "individual"
                        sub_layout.margins_top = safe_text(m_node.find("top"), "0")
                        sub_layout.margins_bottom = safe_text(m_node.find("bottom"), "0")
                        sub_layout.margins_left = safe_text(m_node.find("left"), "0")
                        sub_layout.margins_right = safe_text(m_node.find("right"), "0")

                h_align = child.find("horizontal-alignment")
                if h_align is not None: sub_layout.horiz_align = safe_text(h_align, "center")
                v_align = child.find("vertical-alignment")
                if v_align is not None: sub_layout.vert_align = safe_text(v_align, "center")

                sizing = child.find("sizing")
                if sizing is not None:
                    h_xml = sizing.find("horizontal")
                    if h_xml is not None:
                        sub_layout.width_method = h_xml.get("method", "content")
                        sub_layout.width_value = safe_text(h_xml, "100")
                    v_xml = sizing.find("vertical")
                    if v_xml is not None:
                        sub_layout.height_method = v_xml.get("method", "content")
                        sub_layout.height_value = safe_text(v_xml, "100")
                
                surf_node = child.find("surface")
                if surf_node is not None:
                    if surf_node.find("panel") is not None:
                        sub_layout.surface_type = "panel-dark"
                    elif surf_node.find("vanilla-translucent") is not None:
                        sub_layout.surface_type = "vanilla-translucent"
                    elif surf_node.find("flat") is not None:
                        sub_layout.surface_type = "flat-black"
                    else:
                        sub_layout.surface_type = "none"
                else:
                    sub_layout.surface_type = "none"
                    
                parent_obj.add_child(sub_layout)
                
                # CORREZIONE IMPORTER GERARCHICO: Parsa direttamente i tag interni saltando <children> se è scroll o drag
                if l_type in ["Scroll Container", "Draggable Container"]:
                    for sub in child:
                        if sub.tag not in ["sizing", "margins", "padding", "surface", "text", "horizontal-alignment", "vertical-alignment", "children"]:
                            self.parse_xml_recursive([sub], sub_layout)
                            break
                else:
                    inner_children = child.find("children")
                    if inner_children is not None: self.parse_xml_recursive(inner_children, sub_layout)
                
            elif child.tag in ["button", "label", "text-box", "text-area", "box", "spacer"]:
                w_id = child.get("id", f"{child.tag}_{self.widget_counter}")
                if f"{child.tag}_{self.widget_counter}" == w_id:
                    self.widget_counter += 1
                text_node = child.find("text")
                w_text = safe_text(text_node, "")
                
                leaf_node = UIComponent(w_id, comp_type=child.tag, text=w_text)
                
                p_node = child.find("padding")
                if p_node is not None:
                    all_node = p_node.find("all")
                    if all_node is not None:
                        leaf_node.padding_type = "all"
                        leaf_node.padding_all = safe_text(all_node, "0")
                    else:
                        leaf_node.padding_type = "individual"
                        leaf_node.padding_top = safe_text(p_node.find("top"), "0")
                        leaf_node.padding_bottom = safe_text(p_node.find("bottom"), "0")
                        leaf_node.padding_left = safe_text(p_node.find("left"), "0")
                        leaf_node.padding_right = safe_text(p_node.find("right"), "0")

                m_node = child.find("margins")
                if m_node is not None:
                    all_node = m_node.find("all")
                    if all_node is not None:
                        leaf_node.margins_type = "all"
                        leaf_node.margins_all = safe_text(all_node, "0")
                    else:
                        leaf_node.margins_type = "individual"
                        leaf_node.margins_top = safe_text(m_node.find("top"), "0")
                        leaf_node.margins_bottom = safe_text(m_node.find("bottom"), "0")
                        leaf_node.margins_left = safe_text(m_node.find("left"), "0")
                        leaf_node.margins_right = safe_text(m_node.find("right"), "0")

                if child.tag == "label":
                    sh = child.find("shadow")
                    if sh is not None: leaf_node.label_shadow = safe_text(sh, "false")
                    mw = child.find("max-width")
                    if mw is not None: leaf_node.label_max_width = safe_text(mw, "")

                if child.tag == "text-box":
                    ml = child.find("max-length")
                    if ml is not None: leaf_node.text_box_max_length = safe_text(ml, "")

                if child.tag == "text-area":
                    ml = child.find("max-length")
                    if ml is not None: leaf_node.text_area_max_length = safe_text(ml, "")
                    mlines = child.find("max-lines")
                    if mlines is not None: leaf_node.text_area_max_lines = safe_text(mlines, "")
                    dc = child.find("display-char-count")
                    if dc is not None: leaf_node.text_area_display_char_count = safe_text(dc, "false")

                if child.tag == "box":
                    color = child.find("color")
                    if color is not None:
                        leaf_node.box_color_mode = "single"
                        leaf_node.box_color = safe_text(color, "")
                    else:
                        sc = child.find("start-color")
                        ec = child.find("end-color")
                        if sc is not None or ec is not None:
                            leaf_node.box_color_mode = "gradient"
                            if sc is not None: leaf_node.box_start_color = safe_text(sc, "")
                            if ec is not None: leaf_node.box_end_color = safe_text(ec, "")
                        d = child.find("direction")
                        if d is not None: leaf_node.box_direction = safe_text(d, "top-to-bottom")
                    fill = child.find("fill")
                    if fill is not None: leaf_node.box_fill = safe_text(fill, "false")

                if child.tag == "spacer":
                    leaf_node.spacer_percent = child.get("percent", "")

                sizing = child.find("sizing")
                if sizing is not None:
                    h_xml = sizing.find("horizontal")
                    if h_xml is not None:
                        leaf_node.width_method = h_xml.get("method", "content")
                        leaf_node.width_value = safe_text(h_xml, "100")
                    v_xml = sizing.find("vertical")
                    if v_xml is not None:
                        leaf_node.height_method = v_xml.get("method", "content")
                        leaf_node.height_value = safe_text(v_xml, "20")
                
                parent_obj.add_child(leaf_node)

if __name__ == "__main__":
    root = tk.Tk()
    app = OwoQtDesigner(root)
    root.mainloop()