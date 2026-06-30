import tkinter as tk
from tkinter import ttk
import json
from datetime import datetime
import platform
from utils import format_number, set_window_geometry_and_center

class ToolTip:
    """
    A simple tooltip widget for Tkinter.
    """
    def __init__(self, widget):
        self.widget = widget
        self.tip_window = None
        self.id = None
        self.x = 0
        self.y = 0

    def show_tip(self, text, x, y):
        """Display text in tooltip window"""
        self.text = text
        if self.tip_window or not self.text:
            return
        # Position the tooltip window relative to the mouse cursor
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True) # Ensure tooltip is above other windows

        label = ttk.Label(tw, text=self.text, justify=tk.LEFT,
                          background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                          font=("Arial", "11", "normal"), wraplength=400, padding=(10, 5))
        label.pack()

    def hide_tip(self):
        """Hide the tooltip window"""
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

class DetailPanel(ttk.Frame):
    """
    A widget to display JSON-like data (dictionaries and lists) in a tree view
    with search/filter functionality and collapsible nodes.
    """
    def __init__(self, parent, data=None, view_raw_data_title="Raw Data View", on_close=None, on_prev_item=None, on_next_item=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.data = data
        self.view_raw_data_title = view_raw_data_title
        self.on_close = on_close
        self.on_prev_item = on_prev_item
        self.on_next_item = on_next_item
        self._sort_alphabetical = False
        self._full_values = {} # Store full values for tooltips
        self._setup_ui()
        self.tooltip = ToolTip(self.tree) # Initialize tooltip
        if data is not None:
            self.load_data(data)

    def _setup_ui(self):
        # Configure grid layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1) # Treeview row

        # Filter Frame (top)
        filter_frame = ttk.Frame(self)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search_change)
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Clear button
        ttk.Button(filter_frame, text="Clear", command=self._clear_search).pack(side=tk.LEFT, padx=(5, 0))

        # Treeview with scrollbars (middle)
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        
        self.tree = ttk.Treeview(tree_frame, columns=("value",), selectmode="browse")
        self.tree.heading("#0", text="Key (Click to Sort)", command=self._toggle_sort_order)
        self.tree.heading("value", text="Value")
        self.tree.column("#0", width=200, minwidth=100)
        self.tree.column("value", width=300, minwidth=200)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Motion>", self._on_tree_hover)
        self.tree.bind("<Leave>", self._on_tree_leave)
        
        # Navigation bindings
        top_level = self.winfo_toplevel()
        if self.on_prev_item:
            self.tree.bind("<Up>", lambda e: self.on_prev_item())
            # Bind to top-level window as well for better UX
            top_level.bind("<Up>", lambda e: self._handle_prev_item(e))
            
        if self.on_next_item:
            self.tree.bind("<Down>", lambda e: self.on_next_item())
            # Bind to top-level window as well for better UX
            top_level.bind("<Down>", lambda e: self._handle_next_item(e))

        # Action Buttons Frame (bottom)
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        ttk.Button(button_frame, text="Expand", command=self.expand_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Expand All", command=self.expand_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Collapse All", command=self.collapse_all).pack(side=tk.LEFT, padx=2)
        
        # Pack Right-aligned buttons (First packed is right-most)
        close_cmd = self.on_close if self.on_close else self.winfo_toplevel().destroy
        ttk.Button(button_frame, text="Close", command=close_cmd).pack(side=tk.RIGHT, padx=2)
            
        ttk.Button(button_frame, text="View Raw Data", command=self.view_raw_data).pack(side=tk.RIGHT, padx=2)

        def handle_close_shortcut(event=None):
            close_cmd()
            return "break"

        if platform.system() == 'Darwin':
            top_level.bind("<Command-w>", handle_close_shortcut)
        else:
            top_level.bind("<Control-w>", handle_close_shortcut)

    def _handle_prev_item(self, event):
        """Handle previous item navigation from top-level binding."""
        if self.on_prev_item:
            self.on_prev_item()
        return "break"

    def _handle_next_item(self, event):
        """Handle next item navigation from top-level binding."""
        if self.on_next_item:
            self.on_next_item()
        return "break"

    def load_data(self, data):
        """Load new data into the tree view."""
        self.data = data
        self._refresh_tree()
        self.expand_all()

    def _clear_search(self):
        self.search_var.set("")
        self.search_entry.focus_set()

    def _on_search_change(self, *args):
        # Debounce could be added here for very large datasets, 
        # but for typical JSON responses direct update is usually fine.
        term = self.search_var.get().strip().lower()
        self._refresh_tree(term)

    def _toggle_sort_order(self):
        """Toggle between alphabetical sort and original insertion order."""
        self._sort_alphabetical = not self._sort_alphabetical
        # Refresh tree with current filter
        term = self.search_var.get().strip().lower()
        self._refresh_tree(term)

    def _refresh_tree(self, search_term=""):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if self.data is None:
            return

        # Populate tree
        # If root data is primitive, just show it
        if not isinstance(self.data, (dict, list, tuple)):
            display_value = self._format_tree_value("Root", self.data)
            if not search_term or search_term in display_value.lower():
                item_id = self.tree.insert("", "end", text="Root", values=(display_value,))
                self._full_values[item_id] = display_value
            return

        self._populate_node("", self.data, search_term)

    def _format_tree_value(self, key, value):
        """Format values for the tree view without altering raw-data mode."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return str(value).lower()
        if key in ["last_updated", "created_at"] and isinstance(value, (int, float)):
            try:
                dt_object = datetime.fromtimestamp(value)
                return dt_object.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                return str(value)
        if isinstance(value, (int, float)):
            return format_number(value)
        return str(value)

    def _populate_node(self, parent_id, data, search_term, container_label=None):
        """
        Recursively populates the tree.
        Returns True if this node or any of its children matched the search_term.
        """
        has_match = False
        
        # Prepare items to iterate
        if isinstance(data, dict):
            if self._sort_alphabetical:
                items = sorted(data.items())
            else:
                items = data.items()
        elif isinstance(data, (list, tuple)):
            items = enumerate(data)
        else:
            return False

        for key, value in items:
            if isinstance(data, dict):
                node_text = str(key)
            else:
                node_text = f"{container_label}[{key}]" if container_label else f"[{key}]"
            node_value = ""
            is_container = isinstance(value, (dict, list, tuple))
            
            if not is_container:
                node_value = self._format_tree_value(key, value)
            
            # Determine if this specific node matches
            match_self = False
            if search_term:
                # Match against key
                if search_term in node_text.lower():
                    match_self = True
                # Match against value (if primitive)
                if not is_container and search_term in node_value.lower():
                    match_self = True
            else:
                # If no search term, everything matches
                match_self = True

            # Tentatively insert the node
            # We insert it closed by default, unless searching
            item_id = self.tree.insert(parent_id, "end", text=node_text, values=(node_value,), open=False)
            if not is_container: # Only store full value for leaf nodes
                self._full_values[item_id] = node_value
            
            children_match = False
            if is_container:
                children_match = self._populate_node(item_id, value, search_term, node_text)
            
            # Filter logic
            if search_term:
                if match_self or children_match:
                    has_match = True
                    # If children matched, expand to show them.
                    # If only self matched (e.g. key matched), we can keep it closed or open.
                    # Let's open it if children matched, so user sees the context.
                    if children_match:
                        self.tree.item(item_id, open=True)
                    # If match_self is True but no children match (or no children), 
                    # we show the node. If it's a container and match_self is True,
                    # we might want to expand it to show the content? 
                    # Let's keep it collapsed if only key matched, unless it's a leaf.
                else:
                    # No match here or in children, remove it
                    self.tree.delete(item_id)
            else:
                # No filter, keep everything.
                # Just return True to propagate existence (though not strictly used for filtering here)
                has_match = True
                
        return has_match

    def expand_all(self):
        """Recursively expand all nodes."""
        def _expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                _expand(child)
        for item in self.tree.get_children():
            _expand(item)

    def expand_selected(self):
        """Expand the selected node and all of its descendants."""
        selected_items = self.tree.selection()
        if not selected_items:
            return

        def _expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                _expand(child)

        for item in selected_items:
            _expand(item)

    def collapse_all(self):
        """Recursively collapse all nodes."""
        def _collapse(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                _collapse(child)
        for item in self.tree.get_children():
            _collapse(item)

    def _on_tree_hover(self, event):
        """Show tooltip on hover if text is truncated."""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            self.tooltip.hide_tip()
            return

        column = self.tree.identify_column(event.x)
        if column == '#0': # Key column
            # Check if key is truncated
            # item_text = self.tree.item(item_id, 'text')
            # For now, only show tooltip for value column
            self.tooltip.hide_tip()
            return
        elif column == '#1': # Value column (ID is '#1' for the first data column)
            full_text = self._full_values.get(item_id)

            if full_text:
                # Check if the displayed text is truncated.
                # This is a heuristic, as Treeview doesn't expose actual truncation state.
                bbox = self.tree.bbox(item_id, column)
                if bbox:
                    # Estimate if text is wider than column. This is not perfect.
                    # A more robust solution might involve measuring text width.
                    column_width = self.tree.column(column, 'width')
                    displayed_text = self.tree.item(item_id, 'values')[0] if self.tree.item(item_id, 'values') else ''
                    if len(full_text) > len(displayed_text) or len(full_text) > (column_width / 8): # Approx char width
                        self.tooltip.show_tip(full_text, event.x_root + 10, event.y_root + 10) # Offset tooltip slightly
                        return
        self.tooltip.hide_tip()

    def _on_tree_leave(self, event):
        """Hide tooltip when mouse leaves the treeview."""
        self.tooltip.hide_tip()

    def view_raw_data(self):
        """Display the underlying data in a plain-text modal with syntax highlighting."""
        if self.data is None:
            return

        top = tk.Toplevel(self)
        top.title(self.view_raw_data_title)
        
        # Use the utility function to set geometry and center
        set_window_geometry_and_center(top, 600, 450, parent=self.winfo_toplevel(), grab=True, make_transient=True)
        
        # Configure grid weight for resizing
        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)

        text_frame = ttk.Frame(top)
        text_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        text_area = tk.Text(text_frame, wrap="word", font=("Courier New", 10))
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=text_area.yview)
        hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=text_area.xview)
        text_area.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure tags for syntax highlighting
        text_area.tag_configure("key", foreground="blue", font=("Courier New", 10, "bold"))
        text_area.tag_configure("string", foreground="green")
        text_area.tag_configure("number", foreground="#D35400") # Dark Orange
        text_area.tag_configure("bool", foreground="purple", font=("Courier New", 10, "bold"))
        text_area.tag_configure("null", foreground="gray", font=("Courier New", 10, "italic"))
        text_area.tag_configure("brace", foreground="black")

        # Button Frame
        btn_frame = ttk.Frame(top)
        btn_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        def copy_to_clipboard():
            json_str = json.dumps(self.data, indent=2)
            top.clipboard_clear()
            top.clipboard_append(json_str)
            top.update() # Required for clipboard append to work on some systems
            copy_btn.config(text="Copied!")
            top.after(2000, lambda: copy_btn.config(text="Copy"))

        copy_btn = ttk.Button(btn_frame, text="Copy", command=copy_to_clipboard)
        copy_btn.pack(side=tk.LEFT)

        ttk.Button(btn_frame, text="Close", command=top.destroy).pack(side=tk.RIGHT)
        
        # Insert formatted JSON
        try:
            self._insert_colored_json(text_area, self.data)
        except Exception as e:
            text_area.insert("1.0", f"Error formatting JSON: {e}\n\n")
            text_area.insert(tk.END, str(self.data))
            
        text_area.configure(state="disabled") # Read-only
        
        # Focus the dialog
        top.transient(self.winfo_toplevel())
        top.grab_set()
        top.focus_set()
        
        # Bind <Escape> key to close the dialog
        top.bind('<Escape>', lambda e: top.destroy())

    def _insert_colored_json(self, text_widget, data, indent_level=0):
        """Recursively insert JSON data with syntax highlighting."""
        indent = "  " * indent_level
        
        if isinstance(data, dict):
            text_widget.insert(tk.END, "{\n", "brace")
            keys = list(data.keys())
            for i, key in enumerate(keys):
                text_widget.insert(tk.END, indent + "  ")
                text_widget.insert(tk.END, f'"{key}"', "key")
                text_widget.insert(tk.END, ": ", "brace")
                self._insert_colored_json(text_widget, data[key], indent_level + 1)
                if i < len(keys) - 1:
                    text_widget.insert(tk.END, ",")
                text_widget.insert(tk.END, "\n")
            text_widget.insert(tk.END, indent + "}", "brace")
            
        elif isinstance(data, list):
            text_widget.insert(tk.END, "[\n", "brace")
            for i, item in enumerate(data):
                text_widget.insert(tk.END, indent + "  ")
                self._insert_colored_json(text_widget, item, indent_level + 1)
                if i < len(data) - 1:
                    text_widget.insert(tk.END, ",")
                text_widget.insert(tk.END, "\n")
            text_widget.insert(tk.END, indent + "]", "brace")
            
        elif isinstance(data, str):
            text_widget.insert(tk.END, json.dumps(data), "string")
            
        elif isinstance(data, bool):
            text_widget.insert(tk.END, str(data).lower(), "bool")
            
        elif data is None:
            text_widget.insert(tk.END, "null", "null")
            
        elif isinstance(data, (int, float)):
            text_widget.insert(tk.END, str(data), "number")
            
        else:
            text_widget.insert(tk.END, str(data))

if __name__ == "__main__":
    # Test the widget
    root = tk.Tk()
    root.title("Detail Panel Test")
    root.geometry("800x600")
    
    test_data = {
        "name": "Mission Alpha",
        "id": "12345",
        "stats": {
            "drones": 5,
            "duration": 120.5,
            "success": True,
            "nested": {
                "a": 1,
                "b": [1, 2, 3]
            }
        },
        "drones": [
            {"id": "D1", "status": "active", "battery": 85},
            {"id": "D2", "status": "returning", "battery": 20},
            {"id": "D3", "status": "idle", "battery": 100}
        ],
        "logs": [
            "Started mission",
            "Waypoint 1 reached",
            "Error: signal lost D2"
        ]
    }
    
    panel = DetailPanel(root, data=test_data, view_raw_data_title="Mission Alpha Raw Data")
    panel.pack(fill="both", expand=True, padx=10, pady=10)
    
    root.mainloop()
